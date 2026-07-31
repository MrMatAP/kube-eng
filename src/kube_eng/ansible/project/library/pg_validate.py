#!/usr/bin/python

import psycopg2

__metaclass__ = type

DOCUMENTATION = r"""
---
module: pg_validate
short_description: Validate PostgreSQL connectivity
description:
- Validate PostgreSQL connectivity
options:
    pg_admin_dsn:
        description: The PostgreSQL Admin DSN
author:
- MrMat (@MrMatAP)
"""

EXAMPLES = r"""
- name: Validate PostgreSQL connectivity
  pg_validate:
    admin_dsn: postgresql://...
"""

RETURN = r"""
status:
  description: All required entitlements are granted
  type: bool
msg:
  description: Output message
  type: str
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

def run_module():
    module_args = dict(
        admin_dsn=dict(type='str', required=True)
    )
    result = dict(status=False, msg='')
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    if module.check_mode:
        module.exit_json(**result)

    try:
        with psycopg2.connect(dsn=module.params['admin_dsn']) as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT rolcreaterole, rolcreatedb FROM pg_roles where rolname = current_user;')
                entitlements = cur.fetchone()
                if entitlements is not None and all(entitlements):
                    result['status'] = True
                    result['msg'] = 'Connectivity and entitlements are granted'
                else:
                    result['status'] = False
                    result['msg'] = 'Missing connectivity or entitlements'
        module.exit_json(**result)
    except psycopg2.Error as e:
        result['status'] = False
        result['msg'] = e.pgerror or 'Unknown Error'
        module.fail_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
