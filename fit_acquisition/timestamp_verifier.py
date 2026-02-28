#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

from __future__ import annotations

import hashlib

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from pyasn1.codec.der import decoder, encoder
from pyasn1.error import PyAsn1Error
from pyasn1.type import univ
import rfc3161ng
from rfc3161ng.api import (
    RemoteTimestamper,
    get_hash_class_from_oid,
    get_hash_from_oid,
    get_hash_oid,
    id_attribute_messageDigest,
    load_certificate,
)


def check_timestamp_with_certificate(
    tst,
    certificate: bytes,
    data: bytes | None = None,
    digest: bytes | None = None,
    hashname: str | None = None,
    nonce: int | None = None,
) -> bool:
    hashname = hashname or "sha1"
    hashobj = hashlib.new(hashname)
    if digest is None:
        if data is None:
            raise ValueError(
                "check_timestamp_with_certificate requires data or digest argument"
            )
        hashobj.update(data)
        digest = hashobj.digest()

    if not isinstance(tst, rfc3161ng.TimeStampToken):
        tst, substrate = decoder.decode(tst, asn1Spec=rfc3161ng.TimeStampToken())
        if substrate:
            raise ValueError("extra data after tst")

    signed_data = tst.content
    certificate_obj = load_certificate(signed_data, certificate)
    if nonce is not None and int(tst.tst_info["nonce"]) != int(nonce):
        raise ValueError("nonce is different or missing")

    message_imprint = tst.tst_info.message_imprint
    if (
        message_imprint.hash_algorithm[0] != get_hash_oid(hashname)
        or bytes(message_imprint.hashed_message) != digest
    ):
        raise ValueError("Message imprint mismatch")

    if not len(signed_data["signerInfos"]):
        raise ValueError("No signature")

    signer_info = signed_data["signerInfos"][0]
    if tst.content["contentInfo"]["contentType"] != rfc3161ng.id_ct_TSTInfo:
        raise ValueError(
            "Signed content type is wrong: %s != %s"
            % (
                tst.content["contentInfo"]["contentType"],
                rfc3161ng.id_ct_TSTInfo,
            )
        )

    content = bytes(
        decoder.decode(
            bytes(tst.content["contentInfo"]["content"]),
            asn1Spec=univ.OctetString(),
        )[0]
    )

    if len(signer_info["authenticatedAttributes"]):
        authenticated_attributes = signer_info["authenticatedAttributes"]
        signer_digest_algorithm = signer_info["digestAlgorithm"]["algorithm"]
        signer_hash_class = get_hash_class_from_oid(signer_digest_algorithm)
        signer_hash_name = get_hash_from_oid(signer_digest_algorithm)
        content_digest = signer_hash_class(content).digest()
        for authenticated_attribute in authenticated_attributes:
            if authenticated_attribute[0] == id_attribute_messageDigest:
                try:
                    signed_digest = bytes(
                        decoder.decode(
                            bytes(authenticated_attribute[1][0]),
                            asn1Spec=univ.OctetString(),
                        )[0]
                    )
                    if signed_digest != content_digest:
                        raise ValueError("Content digest != signed digest")
                    signed_attrs = univ.SetOf()
                    for index, value in enumerate(authenticated_attributes):
                        signed_attrs.setComponentByPosition(index, value)
                    signed_payload = encoder.encode(signed_attrs)
                    break
                except PyAsn1Error:
                    raise
        else:
            raise ValueError("No signed digest")
    else:
        signer_hash_name = get_hash_from_oid(signer_info["digestAlgorithm"]["algorithm"])
        signed_payload = content

    signature = bytes(signer_info["encryptedDigest"])
    hash_algorithm = getattr(hashes, signer_hash_name.upper())()
    public_key = certificate_obj.public_key()
    if isinstance(public_key, rsa.RSAPublicKey):
        public_key.verify(
            signature,
            signed_payload,
            padding.PKCS1v15(),
            hash_algorithm,
        )
    elif isinstance(public_key, ec.EllipticCurvePublicKey):
        public_key.verify(
            signature,
            signed_payload,
            ec.ECDSA(hash_algorithm),
        )
    else:
        raise ValueError(f"Unsupported public key type: {type(public_key)!r}")

    return True


def request_timestamp_token(
    url: str,
    data: bytes,
    certificate: bytes,
    hashname: str = "sha256",
    timeout: int = 10,
    include_tsa_certificate: bool = False,
    username: str | None = None,
    password: str | None = None,
    nonce: int | None = None,
    tsa_policy_id: str | None = None,
) -> bytes:
    timestamper = RemoteTimestamper(
        url,
        hashname=hashname,
        timeout=timeout,
        include_tsa_certificate=include_tsa_certificate,
        username=username,
        password=password,
        tsa_policy_id=tsa_policy_id,
    )
    tsr = timestamper(data=data, nonce=nonce, return_tsr=True)
    check_timestamp_with_certificate(
        tsr.time_stamp_token,
        certificate=certificate,
        data=data,
        hashname=hashname,
        nonce=nonce,
    )
    return encoder.encode(tsr.time_stamp_token)
