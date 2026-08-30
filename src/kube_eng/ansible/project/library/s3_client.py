from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.s3_utils import S3Admin, S3Exception

_UNSET_ = '--UNSET--'


def run_module():
    module_args = {
        's3_endpoint': {'type': 'str', 'required': True},
        's3_access_key': {'type': 'str', 'required': True},
        's3_secret_key': {'type': 'str', 'required': True, 'no_log': True},
        's3_region': {'type': 'str', 'required': True},
        's3_ca_path': {'type': 'str', 'required': True},
        # The identity being managed. Used as the IAM user name and, when
        # 'policy' is given, as the policy name (the svc-<service> 1:1
        # convention -- see ADR-0003).
        'access_key': {'type': 'str', 'required': True},
        'secret_key': {
            'type': 'str',
            'required': False,
            'default': _UNSET_,
            'no_log': True,
        },
        # Inline policy document to author under 'access_key'. Omit to only
        # attach pre-existing policies (e.g. canned ones) named in 'policies'.
        # With state=absent, passing 'policy' (any document) also removes the
        # 'access_key'-named policy; omit it to remove just the account.
        'policy': {'type': 'dict', 'required': False, 'default': None},
        # Pre-existing policy names to attach to the IAM user, in addition to
        # 'access_key' itself when 'policy' is set.
        'policies': {
            'type': 'list',
            'elements': 'str',
            'required': False,
            'default': [],
        },
        'state': {
            'type': 'str',
            'required': False,
            'default': 'present',
            'choices': ['present', 'absent'],
        },
    }
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    if module.check_mode:
        module.exit_json()

    access_key = module.params['access_key']
    secret_key = module.params['secret_key']
    policy = module.params['policy']
    manage_account = secret_key != _UNSET_

    if module.params['state'] == 'present' and not manage_account and policy is None:
        module.fail_json(
            msg='state=present needs a secret_key (to manage an account), '
            'a policy (to author one), or both'
        )

    try:
        s3_admin = S3Admin(
            s3_endpoint=module.params['s3_endpoint'],
            s3_access_key=module.params['s3_access_key'],
            s3_secret_key=module.params['s3_secret_key'],
            s3_region=module.params['s3_region'],
            s3_ca_path=module.params['s3_ca_path'],
        )

        if module.params['state'] == 'present':
            changed = False
            messages = []
            result = {'access_key': access_key}
            if policy is not None:
                pr = s3_admin.policy_ensure(access_key, policy)
                changed = changed or pr.changed
                messages.append(pr.msg)
            if manage_account:
                attach = ([access_key] if policy is not None else []) + module.params[
                    'policies'
                ]
                # secret_key is one of this module's own inputs (never
                # regenerated), so its value doesn't need no_log_values
                # scrubbing from the JSON result the caller relies on.
                ar = s3_admin.account_ensure(access_key, secret_key, attach)
                changed = changed or ar.changed
                messages.append(ar.msg)
                result['policies'] = ar.policies
            result['changed'] = changed
            result['msg'] = '; '.join(messages)
        else:
            ar = s3_admin.account_remove(access_key)
            changed = ar.changed
            messages = [ar.msg]
            # Only remove the policy when the caller passed 'policy',
            # asserting the svc-<service> policy is theirs to delete -- the
            # 1:1 access_key/policy-name convention lives in the playbook,
            # not in this module's inputs.
            if policy is not None:
                pr = s3_admin.policy_remove(access_key)
                changed = changed or pr.changed
                messages.append(pr.msg)
            result = {
                'changed': changed,
                'access_key': access_key,
                'msg': '; '.join(messages),
            }

        module.exit_json(**result)
    except S3Exception as e:
        module.fail_json(**e.ansible_result())


def main():
    run_module()


if __name__ == '__main__':
    main()
