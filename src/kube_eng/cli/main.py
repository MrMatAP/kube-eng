import enum
import sys
import pathlib
import argparse
import asyncio
import yaml

import rich.status
from pydantic import BaseModel

from kube_eng import __version__, __default_config_path__
from kube_eng.common.ansible_execution import cmd_to_playbook
from kube_eng.config import RootConfig
from kube_eng.common import AnsibleEvent, AnsibleExecution

console = rich.console.Console()


def _log_ansible_event(ev: AnsibleEvent) -> None:
    """
    Callback to print the outcome of an Ansible event on the CLI console.
    Args:
        ev (AnsibleEvent): The Ansible event to print.
    """
    if ev.event in ['playbook_on_task_start', 'runner_on_start']:
        return
    console.print(f'{ev.status.value}: {ev.task}')

async def config_list(config: RootConfig, args: argparse.Namespace) -> int:
    del args
    console.print(yaml.dump(config.model_dump()))
    return 0

async def config_get(config: RootConfig, args: argparse.Namespace) -> int:
    """
    Print the value of a configuration value in the configuration hierarchy.
    Args:
        config (RootConfig): The root configuration object
        args (): The parsed command line arguments

    Returns:
        An integer exit code
    """
    if 'key' not in args:
        return await config_list(config, args)
    path = args.key.split('.')
    value = config.model_dump(mode='json', exclude_unset=True)
    for p in path:
        value = value[p]
    console.print(yaml.dump(value))
    return 0

async def config_set(config: RootConfig, args: argparse.Namespace) -> int:
    """
    Set a configuration value in the configuration hierarchy.
    Args:
        config (RootConfig): The root configuration object
        args (): The parsed command line arguments

    Returns:
        An integer exit code
    """
    if 'key' not in args or 'value' not in args:
        console.print('Please specify both a key and a value')
        return 1
    path = args.key.split('.')
    parent = config
    leaf = path[-1]
    current_path: list[str] = []
    for container in path[:-1]:
        current_path.append(container)
        if not hasattr(parent, container):
            console.print(f'There is no attribute at {".".join(current_path)}')
            return 1
        parent = getattr(parent, container)
    if not hasattr(parent, leaf):
        console.print(f'There is no attribute at {".".join(current_path + [leaf])}')
        return 1
    if issubclass(type(getattr(parent, leaf)), BaseModel):
        console.print('You cannot set the value of an entire object. Set a path that resolves to an attribute instead.')
        return 1
    if issubclass(type(getattr(parent, leaf)), enum.Enum):
        if args.value not in list(type(getattr(parent, leaf))):
            console.print(f'The value {args.value} is not a valid option for {args.key}')
            return 1
        else:
            setattr(parent, leaf, type(getattr(parent, leaf))(args.value))
    elif isinstance(getattr(parent, leaf), bool):
        setattr(parent, leaf, args.value.lower() == 'true')
    else:
        setattr(parent, leaf, args.value)
    config.save()
    return 0

async def ansible_execute(config: RootConfig, args: argparse.Namespace) -> int:
    """
    Execute the Ansible playbook corresponding to the command.
    Args:
        config (RootConfig): The root configuration object
        args (): The parsed command line arguments

    Returns:
        An integer exit code
    """
    ex = AnsibleExecution(config, _log_ansible_event)
    await ex.execute(playbook=cmd_to_playbook[args.playbook])
    return 0

async def main() -> int:
    try:
        parser = argparse.ArgumentParser(f'Kube-Eng {__version__}')
        parser.add_argument(
            '--config',
            type=pathlib.Path,
            required=False,
            dest='config_path',
            default=__default_config_path__,
            help=f'Path to the config file, defaults to {__default_config_path__}',
        )
        subparsers = parser.add_subparsers(required=True, help='Sub-commands'
        )
        config_parser = subparsers.add_parser('config', help='Configuration commands')
        config_subparser = config_parser.add_subparsers(required=True)
        config_list_parser = config_subparser.add_parser('list', help='List current configuration')
        config_list_parser.set_defaults(func=config_list)
        config_get_parser = config_subparser.add_parser('get', help='Get a configuration value')
        config_get_parser.add_argument('key', help='Setting key')
        config_get_parser.set_defaults(func=config_get)
        config_set_parser = config_subparser.add_parser(
            'set', help='Set a configuration value'
        )
        config_set_parser.add_argument('key', help='Setting key')
        config_set_parser.add_argument(
            'value', help='Value to set for the key'
        )
        config_set_parser.set_defaults(func=config_set)
        apply_host_parser = subparsers.add_parser(
            'host-apply', help='Apply the host configuration'
        )
        apply_host_parser.set_defaults(func=ansible_execute, playbook='host-apply')
        apply_cluster_parser = subparsers.add_parser(
            'cluster-apply', help='Apply the cluster configuration'
        )
        apply_cluster_parser.set_defaults(func=ansible_execute, playbook='cluster-apply')
        destroy_cluster_parser = subparsers.add_parser(
            'cluster-destroy', help='Destroy the cluster'
        )
        destroy_cluster_parser.set_defaults(func=ansible_execute, playbook='cluster-destroy')
        apply_stack_parser = subparsers.add_parser(
            'stack-apply', help='Apply the stack configuration'
        )
        apply_stack_parser.set_defaults(func=ansible_execute, playbook='stack-apply')

        helm_repackage_parser = subparsers.add_parser('helm-repackage', help='Repackage Helm charts')
        helm_repackage_parser.set_defaults(func=ansible_execute, playbook='helm-repackage')

        args = parser.parse_args()
        config = RootConfig.load(config_path=args.config_path)
        config.save()
        return await args.func(config, args)
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(e)
    return 1

def run() -> int:
    return asyncio.run(main())


if __name__ == '__main__':
    sys.exit(run())
