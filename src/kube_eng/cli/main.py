import sys
import pathlib
import argparse
import asyncio

import rich.status

from kube_eng import __version__, __default_config_path__
from kube_eng.common.ansible_execution import cmd_to_playbook
from kube_eng.config import RootConfig
from kube_eng.common import AnsibleEvent, AnsibleExecution

console = rich.console.Console()

def log_ansible_event(ev: AnsibleEvent) -> None:
    """
    Prints events that completed and those that have no completion to the
    console.
    Args:
        ev (AnsibleEvent): The Ansible event to print.
    """
    if ev.event in ['playbook_on_task_start', 'runner_on_start']:
        return
    console.print(f"{ev.status.value}: {ev.task}")

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
        subparsers = parser.add_subparsers(dest='command', required=True, help='Sub-commands')
        apply_host_parser = subparsers.add_parser('host-apply', help='Apply the host configuration')
        apply_cluster_parser = subparsers.add_parser('cluster-apply', help='Apply the cluster configuration')
        destroy_cluster_parser = subparsers.add_parser('cluster-destroy', help='Destroy the cluster')
        apply_stack_parser = subparsers.add_parser('stack-apply', help='Apply the stack configuration')
        args = parser.parse_args()
        config = RootConfig.load(config_path=args.config_path)
        config.save()

        #
        # Execute the playbook

        if args.command not in cmd_to_playbook.keys():
            parser.print_help()
            return 1
        ex = AnsibleExecution(config, log_ansible_event)
        await ex.execute(playbook=cmd_to_playbook[args.command])
        pass
    except KeyboardInterrupt:
        pass
    except Exception as e:
        pass
    return 0


def run() -> int:
    return asyncio.run(main())


if __name__ == '__main__':
    sys.exit(run())
