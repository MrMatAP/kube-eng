import argparse
import asyncio
import enum
import pathlib
import sys
import typing

import pydantic
import rich.console
import yaml
from pydantic import BaseModel
from rich.padding import Padding

from kube_eng import __default_config_path__, __version__
from kube_eng.common import AnsibleEvent, AnsibleExecution
from kube_eng.common.ansible_execution import AnsibleStatusEnum, cmd_to_playbook
from kube_eng.config import RootConfig, RootConfigAware

console = rich.console.Console()


class CLIAnsibleEventLog:
    _status_display: dict[AnsibleStatusEnum, str] = {  # noqa: RUF012
        AnsibleStatusEnum.ok: 'green',
        AnsibleStatusEnum.unchanged: 'dim green',
        AnsibleStatusEnum.empty: 'dim blue',
        AnsibleStatusEnum.running: 'orange1',
        AnsibleStatusEnum.failed: 'red',
        AnsibleStatusEnum.unknown: 'yellow',
    }

    def __init__(self, ev: AnsibleEvent) -> None:
        self._ev = ev

    def __rich_console__(
        self, _con: rich.console.Console, _options: rich.console.ConsoleOptions
    ):
        color = self._status_display.get(self._ev.status, 'white')
        yield f'{self._ev.status.value} [{color}]{self._ev.task}[/{color}]'
        if self._ev.msg:
            yield Padding(
                self._ev.msg, pad=(0, 2, 0, 4), style=f'dim {color}', expand=True
            )
        if self._ev.verbose:
            yield Padding(
                f'{self._ev.uuid} - {self._ev.event}',
                pad=(0, 2, 0, 4),
                style='blue',
                expand=True,
            )
        if self._ev.stdout:
            yield Padding('Stdout:', pad=(0, 2, 0, 4), style='dim white', expand=True)
            yield Padding(
                self._ev.stdout, pad=(0, 2, 0, 6), style='dim white', expand=True
            )
        if self._ev.stderr:
            yield Padding('Stderr:', pad=(0, 2, 0, 4), style='dim yellow', expand=True)
            yield Padding(
                self._ev.stderr, pad=(0, 2, 0, 6), style='dim yellow', expand=True
            )
        if self._ev.warnings:
            yield Padding('Warnings:', pad=(0, 2, 0, 4), style='yellow', expand=True)
            for warning in self._ev.warnings:
                yield Padding(warning, pad=(0, 2, 0, 6), style='yellow', expand=True)


def _log_ansible_event(ev: AnsibleEvent) -> None:
    """
    Callback to print the outcome of an Ansible event on the CLI console.
    Args:
        ev (AnsibleEvent): The Ansible event to print.
    """
    if ev.event in ['playbook_on_task_start', 'runner_on_start']:
        return
    # console.print(f'{ev.status.value}: {ev.task}')
    console.print(CLIAnsibleEventLog(ev))


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


def _placeholder_value(annotation: typing.Any) -> str:
    """
    An obviously-fake but type-valid value for a required field we have no
    real data for, e.g. when switching a discriminated union's provider
    introduces fields the previous provider never needed.
    Args:
        annotation (): The field's type annotation

    Returns:
        A placeholder string that satisfies the annotation
    """
    if isinstance(annotation, type) and issubclass(annotation, pydantic.AnyUrl):
        return 'https://change-me.example.com'
    return 'change-me.example.com'


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
    leaf = path[-1]

    # Track (object, attribute_name) pairs as we walk down so that, if the
    # leaf turns out to be a discriminator field, we still have a handle on
    # the ancestor whose field actually declares the discriminated union.
    ancestors: list[tuple[BaseModel, str]] = []
    parent = config
    current_path: list[str] = []
    for container in path[:-1]:
        current_path.append(container)
        if not hasattr(parent, container):
            console.print(f'There is no attribute at {".".join(current_path)}')
            return 1
        ancestors.append((parent, container))
        parent = getattr(parent, container)
    if not hasattr(parent, leaf):
        console.print(f'There is no attribute at {".".join(current_path + [leaf])}')
        return 1
    current_value = getattr(parent, leaf)
    if issubclass(type(current_value), BaseModel):
        console.print(
            'You cannot set the value of an entire object. Set a path that resolves to an attribute instead.'
        )
        return 1

    if ancestors:
        grandparent, field_name = ancestors[-1]
        field_info = type(grandparent).model_fields.get(field_name)
        if field_info is not None and field_info.discriminator == leaf:
            # `leaf` picks which model class a discriminated union (e.g.
            # infra.dns: LocalDNSConfig | RemoteDNSConfig) actually is.
            # Mutating it in place would leave an object whose runtime type
            # no longer matches its own fields (still a LocalDNSConfig with
            # provider='remote'), which serializes inconsistently and
            # silently corrupts the saved config. Re-validate the whole
            # union member from its current values plus the new provider.
            merged = {
                **parent.model_dump(mode='json', exclude_computed_fields=True),
                leaf: args.value,
            }
            # The target provider may require fields the current one never
            # had (e.g. a remote fqdn/URL) and that only the user can supply
            # a real value for. Rather than blocking the switch entirely,
            # seed those with an obvious placeholder so it succeeds and the
            # user can fill in the real value with a follow-up `config set`.
            target_cls = next(
                (
                    cls
                    for cls in typing.get_args(field_info.annotation)
                    if cls.model_fields[leaf].default == args.value
                ),
                None,
            )
            defaulted: list[str] = []
            if target_cls is not None:
                for name, target_field in target_cls.model_fields.items():
                    if name not in merged and target_field.is_required():
                        merged[name] = _placeholder_value(target_field.annotation)
                        defaulted.append(name)
            adapter = pydantic.TypeAdapter(field_info.rebuild_annotation())
            try:
                new_value = adapter.validate_python(merged)
            except pydantic.ValidationError as ve:
                console.print(f'Cannot set {args.key} to {args.value!r}:\n{ve}')
                return 1
            setattr(grandparent, field_name, new_value)
            if issubclass(type(new_value), RootConfigAware):
                new_value.propagate_root_config(config)
            config.save()
            if defaulted:
                prefix = '.'.join(path[:-1])
                defaulted.sort()
                console.print(
                    f"Switched {prefix} to '{args.value}'. Placeholder values were "
                    f'set for: {", ".join(defaulted)} -- update them, e.g. '
                    f"'kube-eng config set {prefix}.{defaulted[0]} <value>'."
                )
            return 0

    if issubclass(type(current_value), enum.Enum):
        if args.value not in list(type(current_value)):
            console.print(
                f'The value {args.value} is not a valid option for {args.key}'
            )
            return 1
        else:
            setattr(parent, leaf, type(current_value)(args.value))
    elif isinstance(current_value, bool):
        setattr(parent, leaf, args.value.lower() == 'true')
    else:
        setattr(parent, leaf, args.value)
    config.save()
    return 0


def _set_nested_value(target: dict, path: list[str], value: typing.Any) -> None:
    current = target
    for part in path[:-1]:
        current = current.setdefault(part, {})
    current[path[-1]] = value


def _collect_overrides(args: argparse.Namespace) -> dict:
    overrides = {}
    for key, value in vars(args).items():
        if not key.startswith('override_') or value is None:
            continue

        _set_nested_value(
            overrides,
            key.removeprefix('override_').split('__'),
            value,
        )

    return overrides


async def ansible_execute(config: RootConfig, args: argparse.Namespace) -> int:
    """
    Execute the Ansible playbook corresponding to the command.
    Args:
        config (RootConfig): The root configuration object
        args (): The parsed command line arguments

    Returns:
        An integer exit code
    """
    overrides = _collect_overrides(args)
    ex = AnsibleExecution(config, _log_ansible_event, verbose=args.verbose)
    await ex.execute(playbook=cmd_to_playbook[args.playbook], overrides=overrides)
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
        parser.add_argument(
            '--verbose',
            '-v',
            action='store_true',
            default=False,
            required=False,
            dest='verbose',
            help='Enable verbose output',
        )
        subparsers = parser.add_subparsers(required=True, help='Sub-commands')
        config_parser = subparsers.add_parser('config', help='Configuration commands')
        config_subparser = config_parser.add_subparsers(required=True)
        config_list_parser = config_subparser.add_parser(
            'list', help='List current configuration'
        )
        config_list_parser.set_defaults(func=config_list)
        config_get_parser = config_subparser.add_parser(
            'get', help='Get a configuration value'
        )
        config_get_parser.add_argument('key', help='Setting key')
        config_get_parser.set_defaults(func=config_get)
        config_set_parser = config_subparser.add_parser(
            'set', help='Set a configuration value'
        )
        config_set_parser.add_argument('key', help='Setting key')
        config_set_parser.add_argument('value', help='Value to set for the key')
        config_set_parser.set_defaults(func=config_set)
        apply_infra_parser = subparsers.add_parser(
            'infra-apply', help='Apply the infrastructure configuration'
        )
        apply_infra_parser.set_defaults(func=ansible_execute, playbook='infra-apply')
        apply_cluster_parser = subparsers.add_parser(
            'cluster-apply', help='Apply the cluster configuration'
        )
        apply_cluster_parser.set_defaults(
            func=ansible_execute, playbook='cluster-apply'
        )
        destroy_cluster_parser = subparsers.add_parser(
            'cluster-destroy', help='Destroy the cluster'
        )
        destroy_cluster_parser.set_defaults(
            func=ansible_execute, playbook='cluster-destroy'
        )
        apply_stack_parser = subparsers.add_parser(
            'stack-apply', help='Apply the stack configuration'
        )
        apply_stack_parser.set_defaults(func=ansible_execute, playbook='stack-apply')

        helm_repackage_parser = subparsers.add_parser(
            'helm-repackage', help='Repackage Helm charts'
        )
        helm_repackage_parser.set_defaults(
            func=ansible_execute, playbook='helm-repackage'
        )
        helm_repackage_parser.add_argument(
            '--registry',
            type=str,
            required=False,
            dest='override_cluster__helm_registry_url',
            help='Helm registry URL',
        )

        dns_update_parser = subparsers.add_parser(
            'dns-update', help='Update DNS records'
        )
        dns_update_parser.set_defaults(func=ansible_execute, playbook='dns-update')

        args = parser.parse_args()
        config = RootConfig.load(config_path=args.config_path)
        config.save()
        return await args.func(config, args)
    except KeyboardInterrupt:
        return 0
    except Exception as e:  # noqa: BLE001
        print(e)
    return 1


def run() -> int:
    return asyncio.run(main())


if __name__ == '__main__':
    sys.exit(run())
