import sys
import asyncio
import dataclasses
import enum
import typing
import collections.abc
import uuid

import ansible_runner
import ansible_runner.config.runner
import rich.emoji

from kube_eng import __ansible_path__
from kube_eng.config import RootConfig

cmd_to_playbook = {
    'host-apply': 'host_apply.yml',
    'cluster-apply': 'cluster_apply.yml',
    'cluster-destroy': 'cluster_destroy.yml',
    'stack-apply': 'stack_apply.yml',

    'helm-repackage': 'helm_repackage.yml',
    'dns-update': 'dns_update.yml',
}

class AnsibleStatusEnum(enum.StrEnum):
    ok = str(rich.emoji.Emoji("ok_button"))
    unchanged = str(rich.emoji.Emoji("pause_button"))
    running = str(rich.emoji.Emoji("repeat_button"))
    failed = str(rich.emoji.Emoji("sos_button"))
    unknown = str(rich.emoji.Emoji("question_mark"))
    empty = str(rich.emoji.Emoji("new_button"))


@dataclasses.dataclass
class AnsibleEvent:
    uuid: str
    counter: int
    event: str
    task: str = dataclasses.field(default='Unknown')
    msg: str = dataclasses.field(default='')
    changed: bool = dataclasses.field(default=False)
    warnings: list[str] = dataclasses.field(default_factory=list)
    status: AnsibleStatusEnum = dataclasses.field(default=AnsibleStatusEnum.empty)
    stdout: str = dataclasses.field(default='')
    stderr: str = dataclasses.field(default='')
    verbose: bool = False


class AnsibleExecution:

    def __init__(self,
                 config: RootConfig,
                 ui_event_callback: collections.abc.Callable[[AnsibleEvent], None],
                 verbose: bool = False):
        self._config = config
        self._ui_event_callback = ui_event_callback
        self._verbose = verbose
        self._cancelled: bool = False

    def cancel(self) -> None:
        """
        Cancel the current Ansible execution.
        """
        self._cancelled = True

    async def execute(self, playbook: str):
        try:
            self._config.ansible_artifacts_path.mkdir(parents=True, exist_ok=True)
            t, r = ansible_runner.run_async(
                ident=f'{playbook}-{uuid.uuid4()}',
                private_data_dir=__ansible_path__,
                playbook=playbook,
                envvars={
                    'ANSIBLE_PYTHON_INTERPRETER': sys.executable,
                    'SSL_CERT_FILE': self._config.host.pki.ca_truststore_path
                },
                extravars=self._config.model_dump(mode="json"),
                suppress_env_files=True,
                artifact_dir=self._config.ansible_artifacts_path,
                rotate_artifacts=5,
                inventory=str(__ansible_path__ / 'inventory' / 'inventory.yml'),
                host_pattern='localhost',
                quiet=True,
                verbosity=2,
                event_handler=self.ansible_event_handler,
                cancel_callback=self.ansible_cancel_callback,
                finished_callback=self.ansible_finished_callback,
                status_handler=self.ansible_status_handler,
                artifacts_handler=self.ansible_artifacts_handler)
            await asyncio.to_thread(t.join)
        except OSError as oe:
            print(f'Failed to create a directory for artefacts of the current Ansible execution: {oe}')
        except Exception as e:
            print(e)

    def ansible_event_handler(self, status: typing.Dict) -> bool:
        ev = AnsibleEvent(uuid=status.get('uuid', 'Unknown'),
                          counter=status.get('counter', 0),
                          event=status.get('event', 'Unknown'),
                          verbose=self._verbose)
        event_data = status.get('event_data', {})
        match ev.event:
            case 'playbook_on_start':
                ev.task = f'Starting playbook {event_data.get("playbook")}'
                ev.status = AnsibleStatusEnum.empty
                ev.msg = 'Started playbook'
            case 'playbook_on_play_start':
                ev.task = f'Starting play {event_data.get("name")}'
                ev.status = AnsibleStatusEnum.empty
                ev.msg = 'Started play'
            case 'playbook_on_task_start':
                ev.task = event_data.get("name")
                ev.status = AnsibleStatusEnum.running
                ev.msg = 'Started task'
            case 'runner_on_start':
                # We do not capture this event
                return True
            case 'runner_on_failed':
                ev.uuid = event_data.get('task_uuid', ev.uuid)
                ev.task = event_data.get('task', 'Unknown')
                ev.msg = event_data.get('res', {}).get('msg', 'Unknown')
                ev.status = AnsibleStatusEnum.failed
                ev.changed = status.get('event_data', {}).get('changed', False)
                self._ui_event_callback(ev)

                # Now create a separate event for the failed task
                ev.uuid = status.get('uuid', 'Unknown')
                ev.task = event_data.get("res", {}).get("msg", "Unknown")
                ev.status = AnsibleStatusEnum.failed
                ev.changed = status.get('event_data', {}).get('changed', False)
                self._ui_event_callback(ev)
                return True
            case 'runner_on_ok':
                # We only run on localhost, re-map the event from the runner
                # uuid to the task uuid
                ev.uuid = event_data.get('task_uuid', ev.uuid)
                ev.task = event_data.get('task', 'Unknown')
                ev.status = AnsibleStatusEnum.ok
                ev.changed = event_data.get('changed', False)
                ev.warnings = event_data.get('res', {}).get('warnings', [])
                ev.msg = event_data.get('res', {}).get('msg', 'Task completed successfully')
                ev.stdout = event_data.get('res', {}).get('stdout', '')
                ev.stderr = event_data.get('res', {}).get('stderr', '')
            case 'error':
                ev.uuid = status.get('uuid', 'Unknown')
                ev.task = event_data.get('task', 'Unknown')
                ev.msg = 'Task failed'
                ev.changed = False
                ev.status = AnsibleStatusEnum.failed
                ev.stdout = status.get('stdout', '')

            case 'playbook_on_stats' | 'playbook_on_include' | 'verbose' | 'runner_item_on_ok' | 'runner_on_skipped' | 'deprecated':
                # We do not capture these events
                return True
            case _:
                ev.task = event_data.get('name', 'Unknown')
        self._ui_event_callback(ev)
        return True

    def ansible_cancel_callback(self) -> bool:
        """
        The Ansible executor will invoke this method to check if the execution should be cancelled.
        Frontends may invoke the cancel method to set a cancellation flag which will be returned to Ansible here.
        Returns:
            True if the execution should be cancelled, False otherwise.
        """
        return self._cancelled

    def ansible_finished_callback(self, runner: ansible_runner.Runner) -> None:
        """
        The Ansible executor will invoke this method when the execution is finished.
        Args:
            runner (ansible_runner.Runner): The Ansible runner instance that completed the execution.
        """
        if runner.status == 'failed':
            ev = AnsibleEvent(uuid='0',
                              counter=0,
                              event='playbook_failed',
                              verbose=self._verbose)
            ev.stdout = runner.stdout.read()
            ev.stderr = runner.stderr.read()
            self._ui_event_callback(ev)

    def ansible_status_handler(self, status_data: typing.Dict, runner_config: ansible_runner.config.runner.RunnerConfig) -> None:
        pass

    def ansible_artifacts_handler(self, artifacts_file: str) -> None:
        pass


