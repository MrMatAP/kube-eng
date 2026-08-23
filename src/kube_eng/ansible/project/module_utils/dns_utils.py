"""DNS-related tooling"""

import datetime
import typing

import dns.exception
import dns.flags
import dns.message
import dns.query
import dns.rcode
import dns.tsig
import dns.tsigkeyring
import dns.update
import pydantic

from .base import InfraException, InfraResult


class DNSException(InfraException):
    pass


class DNSResult(InfraResult):
    pass


class DNSValidationResult(DNSResult):
    validated: typing.Annotated[bool, pydantic.Field()]


class DNSAdmin:
    def __init__(
        self,
        dns_ip: str,
        dns_admin_key_name: str,
        dns_admin_key_secret: str,
        dns_protocol: str = 'tcp',
    ):
        self._dns_ip = dns_ip
        self._admin_key_name = dns_admin_key_name
        self._admin_key_secret = dns_admin_key_secret
        self._query = dns.query.tcp if dns_protocol == 'tcp' else dns.query.udp

    def validate(self, dns_zone: str, dns_domain: str) -> DNSValidationResult:
        """
        Validate connectivity and dynamic-update entitlements against DNS by
        writing a timestamped TXT record and reading it back.
        Args:
            dns_zone (str): The DNS zone hosting the domain
            dns_domain (str): The domain to validate updates against, within dns_zone

        Returns:
            A DNSValidationResult
        Throws:
            DNSException, when connectivity or entitlements are missing
        """
        fqdn = f'kube-eng-dns-validation.{dns_domain}.'
        try:
            soa_query = dns.message.make_query(qname=dns_zone, rdtype='SOA')
            soa = self._query(q=soa_query, where=self._dns_ip)
            if not soa.flags & dns.flags.AA:
                raise DNSException(
                    code=400, msg=f'DNS server is not authoritative for {dns_zone}'
                )

            timestamp = datetime.datetime.now(datetime.UTC).isoformat()
            keyring = dns.tsigkeyring.from_text(
                {self._admin_key_name: self._admin_key_secret}
            )
            dns_update = dns.update.Update(
                dns_zone, keyring=keyring, keyalgorithm=dns.tsig.HMAC_SHA256
            )
            dns_update.replace(fqdn, 60, 'TXT', timestamp)
            update_response = self._query(q=dns_update, where=self._dns_ip)
            if update_response.rcode() != dns.rcode.NOERROR:
                raise DNSException(
                    code=400,
                    msg=f'DNS update failed: {dns.rcode.to_text(update_response.rcode())}',
                )

            txt_query = dns.message.make_query(qname=fqdn, rdtype='TXT')
            txt_response = self._query(q=txt_query, where=self._dns_ip)
            written = ''.join(
                part.decode()
                for rrset in txt_response.answer
                for rdata in rrset
                for part in rdata.strings
            )
            if written != timestamp:
                raise DNSException(
                    code=400,
                    msg=f'TXT record update could not be verified ({written} != {timestamp})',
                )

            return DNSValidationResult(
                changed=False,
                msg='Connectivity and entitlements are granted',
                validated=True,
            )
        except dns.exception.DNSException as de:
            raise DNSException(code=400, msg=str(de) or 'Unknown Error') from de
