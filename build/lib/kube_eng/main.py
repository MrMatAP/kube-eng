import sys
import asyncio
import pathlib
import tempfile

import ansible_runner

async def main() -> int:
    ansible_dun = pathlib.Path(__file__).parent / 'ansible'
    hello_world_playbook = pathlib.Path(__file__).parent / 'ansible' / 'hello_world.yml'
    with tempfile.TemporaryDirectory() as ansible_exec_path:
        # t, r = ansible_runner.run_async(private_data_dir=ansible_dun,
        #                                 playbook=hello_world_playbook)
        r = ansible_runner.run(private_data_dir=ansible_dun,
                                        playbook=hello_world_playbook)
        print('{}: {}'.format(r.status, r.rc))
        # successful: 0
        for each_host_event in r.events:
            print(each_host_event['event'])
        print('Final status:')
        print(r.stats)
    return 0

def run() -> int:
    return asyncio.run(main())

if __name__ == '__main__':
    sys.exit(run())