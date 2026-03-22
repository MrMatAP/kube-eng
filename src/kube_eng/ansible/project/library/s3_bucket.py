#!/usr/bin/python

from __future__ import absolute_import, division, print_function
import boto3
import botocore.client
import botocore.exceptions

__metaclass__ = type

DOCUMENTATION = r"""
---
module: s3_buckets
short_description: Manage S3 buckets
description:
- Manage S3 buckets
options:
    admin_access_key:
        description: The admin access key
        required: true
        type: str
    admin_secret_key:
        description: The admin secret key
        required: true
        type: str
    s3_endpoint:
        description: The S3 endpoint
        required: false
        default: 'https://localhost:9000'
        type: str
    truststore_path:
        description: Path to the trust store
        required: true
        type: str
    bucket_name:
        description: The name of the bucket
        required: true
        type: str
    state:
        description: The desired state of the bucket
        required: false
        type: str
        choices: ['present', 'absent']
        default: present
author:
- MrMat (@MrMatAP)
"""

EXAMPLES = r"""
- name: Create an S3 bucket
  s3_bucket:
    admin_access_key: account
    admin_secret_key: adminsecret
    s3_endpoint: https://localhost:9000
    truststore_path: /path/to/.kube-eng/pki/ca.pem
    bucket_name: my-bucket
    state: present
  
- name: Remove an access key
  s3_account:
    admin_access_key: account
    admin_secret_key: adminsecret
    s3_endpoint: https://localhost:9000
    truststore_path: /path/to/.kube-eng/pki/ca.pem
    bucket_name: my-bucket
    state: absent
"""

RETURN = r"""
changed:
  description: Whether a change was actually performed
  type: bool
msg:
  description: Output message
  type: str
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402


def run_module():
    module_args = dict(
        admin_access_key=dict(type='str', required=True),
        admin_secret_key=dict(type='str', required=True),
        s3_endpoint=dict(type='str', required=False, default='https://localhost:9000'),
        truststore_path=dict(type='str', required=True),
        bucket_name=dict(type='str', required=True),
        state=dict(
            type='str', required=False, default='present', choices=['present', 'absent']
        ),
    )
    result = dict(
        secret_key='',
        changed=False,
        msg='',
    )
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    if module.check_mode:
        module.exit_json(**result)

    try:
        s3 = boto3.client('s3',
                           endpoint_url=module.params['s3_endpoint'],
                           use_ssl=True,
                           verify=module.params['truststore_path'],
                           aws_access_key_id=module.params['admin_access_key'],
                           aws_secret_access_key=module.params['admin_secret_key'],
                           config=botocore.client.Config(signature_version='s3v4'),
                           region_name='us-east-1')
        if module.params['state'] == 'present':
            s3.create_bucket(Bucket=module.params['bucket_name'])
            result['msg'] = 'Bucket created'
        else:
            s3.delete_bucket(Bucket=module.params['bucket_name'])
            result['msg'] = 'Bucket deleted'
    except botocore.exceptions.ClientError as err:
        result['changed'] = False
        code = err.response.get("Error", {}).get("Code", "Unknown")
        if module.params['state'] == 'present' and code == 'BucketAlreadyExists':
            result['msg'] = 'Bucket is present'
            result['changed'] = False
            module.exit_json(**result)
        status_code = err.response.get("ResponseMetadata", {}).get("HTTPStatusCode", "Unknown")
        msg = err.response.get("Error", {}).get("Message", "An unknown error occurred")
        result['msg'] = f'[{status_code}] - {msg}'
        module.fail_json(**result)

    result['changed'] = True
    module.exit_json(**result)

def main():
    run_module()


if __name__ == '__main__':
    main()
