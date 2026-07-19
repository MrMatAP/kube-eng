#!/usr/bin/env python3
"""Display the CN and Issuer of every x509 certificate in a concatenated PEM file."""

import argparse
import pathlib
import sys

from cryptography import x509


def iter_certificates(pem_path: pathlib.Path) -> list[x509.Certificate]:
    data = pem_path.read_bytes()
    marker = b'-----BEGIN CERTIFICATE-----'
    blocks = [marker + block for block in data.split(marker)[1:]]
    return [x509.load_pem_x509_certificate(block) for block in blocks]


def common_name(name: x509.Name) -> str:
    attrs = name.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    if not attrs:
        return name.rfc4514_string()
    value = attrs[0].value
    return value if isinstance(value, str) else value.decode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'pem_file', type=pathlib.Path, help='Path to the concatenated PEM file'
    )
    args = parser.parse_args()

    certificates = iter_certificates(args.pem_file)
    if not certificates:
        print(f'No certificates found in {args.pem_file}', file=sys.stderr)
        return 1

    for index, cert in enumerate(certificates, start=1):
        print(
            f'[{index}] CN={common_name(cert.subject)}  Issuer={common_name(cert.issuer)}'
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
