#!/usr/bin/python

import datetime

import dns.exception
import dns.flags
import dns.message
import dns.query
import dns.rcode
import dns.tsig
import dns.tsigkeyring
import dns.update

__metaclass__ = type

DOCUMENTATION = r"""
---
module: dns_validate
short_description: Validate DNS connectivity and entitlements
description:
- Validate DNS connectivity
options:
    dns_ip:
        description: The DNS server IP address
        required: true
        type: str
    dns_admin_key_name:
        description: The DNS admin TSIG key
        required: true
        type: str
    dns_admin_key_secret:
        description: The DNS admin secret
        required: true
        type: str
    dns_protocol:
        description: The protocol to perform updates over
        required: false
        type: str
        choices: ['tcp', 'udp']
        default: tcp
    dns_zone: 
        description: The DNS zone hosting the domain
        required: true
        type: str
    dns_domain:
        description: The domain to be updated for this cluster. Must be within dns_zone
author:
- MrMat (@MrMatAP)
"""

EXAMPLES = r"""
- name: Validate DNS connectivity and entitlements
  dns_validate:
    dns_ip: 127.0.0.1
    dns_admin_key_name: update_key
    dns_admin_key_secret: secret
    dns_protocol: tcp
    dns_zone: k8s.
    dns_domain: nostromo.k8s.
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
        dns_ip=dict(type='str', required=True),
        dns_admin_key_name=dict(type='str', required=True),
        dns_admin_key_secret=dict(type='str', required=True, no_log=True),
        dns_protocol=dict(type='str', required=False, default='tcp', choices=['tcp', 'udp']),
        dns_zone=dict(type='str', required=True),
        dns_domain=dict(type='str', required=True)
    )
    result = dict(status=False, msg='')
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    if module.check_mode:
        module.exit_json(**result)

    query = dns.query.tcp if module.params['dns_protocol'] == 'tcp' else dns.query.udp
    fqdn = f'kube-eng-dns-validation.{module.params["dns_domain"]}.'

    try:
        # Check the server is authoritative for the zone
        soa_query = dns.message.make_query(qname=module.params['dns_zone'], rdtype='SOA')
        soa = query(q=soa_query, where=module.params['dns_ip'])
        if not soa.flags & dns.flags.AA:
            result['msg'] = f'DNS server is not authoritative for {module.params["dns_zone"]}'
            module.exit_json(**result)

        # Update the validation TXT record with the current timestamp
        timestamp = datetime.datetime.now(datetime.UTC).isoformat()
        keyring = dns.tsigkeyring.from_text({
            module.params['dns_admin_key_name']: module.params['dns_admin_key_secret']
        })
        dns_update = dns.update.Update(module.params['dns_zone'],
                                        keyring=keyring,
                                        keyalgorithm=dns.tsig.HMAC_SHA256)
        dns_update.replace(fqdn, 60, 'TXT', timestamp)
        update_response = query(q=dns_update, where=module.params['dns_ip'])
        if update_response.rcode() != dns.rcode.NOERROR:
            result['msg'] = f'DNS update failed: {dns.rcode.to_text(update_response.rcode())}'
            module.exit_json(**result)

        # Query the record back and check it matches what we just wrote
        txt_query = dns.message.make_query(qname=fqdn, rdtype='TXT')
        txt_response = query(q=txt_query, where=module.params['dns_ip'])
        written = ''.join(
            part.decode()
            for rrset in txt_response.answer
            for rdata in rrset
            for part in rdata.strings
        )

        if written == timestamp:
            result['status'] = True
            result['msg'] = 'Connectivity and entitlements are granted'
        else:
            result['msg'] = f'TXT record update could not be verified ({written} != {timestamp}'
        module.exit_json(**result)
    except dns.exception.DNSException as e:
        result['status'] = False
        result['msg'] = str(e) or 'Unknown Error'
        module.fail_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
