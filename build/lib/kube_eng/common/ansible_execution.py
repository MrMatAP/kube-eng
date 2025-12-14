import dataclasses
import enum
import typing
import collections.abc

import ansible_runner
import rich.emoji

from kube_eng import __ansible_project_dir__
from kube_eng.config import RootConfig


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
    changed: bool = dataclasses.field(default=False)
    warnings: list[str] = dataclasses.field(default_factory=list)
    status: AnsibleStatusEnum = dataclasses.field(default=AnsibleStatusEnum.empty)


class AnsibleExecution:

    def __init__(self, config: RootConfig, ui_event_callback: collections.abc.Callable[[AnsibleEvent], None]):
        self._config = config
        self._ui_event_callback = ui_event_callback

    def execute(self, playbook: str):
        self._config.artifacts_path.mkdir(parents=True, exist_ok=True)
        t, r = ansible_runner.run_async(
            private_data_dir=__ansible_project_dir__,
            artifact_dir=self._config.artifacts_path,
            playbook=playbook,
            extravars=self._config.model_dump(mode="json"),
            host_pattern='localhost',
            event_handler=self.ansible_event_handler,
            finished_callback=self.ansible_finished_callback,
            status_handler=self.ansible_status_handler,
            artifacts_handler=self.ansible_artifacts_handler,
            quiet=True
        )

    def ansible_event_handler(self, status: typing.Dict) -> bool:
        ev = AnsibleEvent(uuid=status.get('uuid', 'Unknown'),
                          counter=status.get('counter', 0),
                          event=status.get('event', 'Unknown'))
        event_data = status.get('event_data', {})
        match ev.event:
            case 'playbook_on_start':
                ev.task = f'Starting playbook {event_data.get("playbook")}'
                ev.status = AnsibleStatusEnum.empty
            case 'playbook_on_play_start':
                ev.task = f'Starting play "{event_data.get("name")}"'
                ev.status = AnsibleStatusEnum.empty
            case 'playbook_on_task_start':
                ev.task = event_data.get("name")
                ev.status = AnsibleStatusEnum.running
            case 'runner_on_start':
                # We do not capture this event
                return True
            case 'runner_on_failed':
                # Update the original task event to have failed first
                ev.uuid = event_data.get('task_uuid', ev.uuid)
                ev.task = event_data.get('task', 'Unknown')
                ev.status = AnsibleStatusEnum.failed
                self._ui_event_callback(ev)

                # Now create a separate event for the failed task
                ev.uuid = status.get('uuid', 'Unknown')
                ev.task = event_data.get("res", {}).get("msg", "Unknown")
                ev.status = AnsibleStatusEnum.failed
                ev.changed = status.get('event_data', {}).get('changed', False)
            case 'runner_on_ok':
                # We only run on localhost, re-map the event from the runner
                # uuid to the task uuid
                ev.uuid = event_data.get('task_uuid', ev.uuid)
                ev.task = event_data.get('task', 'Unknown')
                ev.status = AnsibleStatusEnum.ok
                ev.changed = event_data.get('changed', False)
                ev.warnings = event_data.get('warnings', [])
            case 'playbook_on_stats' | 'playbook_on_include' | 'verbose' | 'runner_item_on_ok' | 'runner_on_skipped' | 'deprecated':
                # We do not capture these events
                return True
            case _:
                ev.task = event_data.get('name', 'Unknown')
        self._ui_event_callback(ev)
        return True

    def ansible_finished_callback(self, runner: ansible_runner.Runner) -> None:
        pass

    def ansible_status_handler(self, status_data: typing.Dict, runner_config) -> None:
        pass

    def ansible_artifacts_handler(self, artifacts_file: str) -> None:
        pass