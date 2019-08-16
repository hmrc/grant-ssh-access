#!/usr/bin/env python3
import os
import traceback
import logging

import boto3
import hvac
import requests
import aws_lambda_logging

DEFAULT_WRAP_TTL = str(60 * 60 * 4)

aws_lambda_logging.setup(level="INFO")


def lambda_handler(event, context):
    logging.info("function invoked")
    return main(event["user_name"], event["ttl"])


def main(user_name, ttl):
    try:
        logging.info("received request to sign key for user")
        ca_cert = os.getenv("CA_CERT", "./mdtp.pem")
        region = os.getenv("REGION", "eu-west-2")
        vault_url = os.getenv("VAULT_URL")

        credentials = aws_authenticate()

        public_key = fetch_public_key(user_name)
        vault_token = vault_authenticate(vault_url, credentials, region, ca_cert)

        vault_session = requests.Session()
        vault_session.verify = ca_cert
        vault_session.headers.update({"X-Vault-Token": vault_token})

        signed_public_key = vault_sign_public_key(
            vault_url, vault_session, user_name, public_key, ttl
        )

        wrap_token = vault_wrap(vault_url, vault_session, signed_public_key)

        return {"token": wrap_token}
    except Exception as e:
        return {"error": str(e), "stacktrace": traceback.format_exc()}


def aws_authenticate():
    """
        Return keys and token for the instances IAM role.
    """
    session = boto3.Session()
    credentials = session.get_credentials()
    credentials = credentials.get_frozen_credentials()

    if not hasattr(credentials, "access_key") or len(credentials.access_key) < 16:
        raise ValueError("Bad credentials provided")
    logging.info("authenticated with aws")

    return credentials


def fetch_public_key(user_name):
    arn_role_cross_account_ssh = os.getenv(
        "CROSS_ACCOUNT_SSH_ARN", "arn:aws:iam::638924580364:role/RoleCrossAccountSSH"
    )
    sts_client = boto3.client("sts")
    assumed = sts_client.assume_role(
        RoleArn=arn_role_cross_account_ssh, RoleSessionName="grant_ssh_access"
    )

    credentials = assumed["Credentials"]

    session = boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )

    iam = session.client("iam")
    key_id = iam.list_ssh_public_keys(UserName=user_name).get("SSHPublicKeys")[0][
        "SSHPublicKeyId"
    ]

    public_key = iam.get_ssh_public_key(
        UserName=user_name, SSHPublicKeyId=key_id, Encoding="SSH"
    )["SSHPublicKey"]["SSHPublicKeyBody"]
    logging.info("fetched public key for user")

    return public_key


def vault_authenticate(vault_url, credentials, region, ca_cert):
    """
        Return Vault client using supplied IAM credentials.
    """
    vault_client = hvac.Client(url=vault_url, verify=ca_cert)
    vault_client.auth_aws_iam(
        credentials.access_key, credentials.secret_key, credentials.token, region=region
    )
    vault_token = vault_client.lookup_token()["data"]["id"]
    logging.info("authenticated with vault")

    return vault_token


def vault_sign_public_key(vault_url, vault_session, user_name, public_key, ttl):
    """
        Use Vault's public key signing API to sign the supplied public key
        with Vault's internal CA.
    """
    url = vault_url + "/v1/ssh-client-signer/sign/vault-role"
    data = {"public_key": public_key, "valid_principals": user_name, "ttl": ttl}

    response = vault_session.post(url, json=data).json()

    try:
        data = response["data"]
        logging.info("signed public key")

        return data
    except KeyError:
        errors = response.get("errors", [])
        raise Exception("Certificate signing failed.  " + "; ".join(errors))


def vault_wrap(vault_url, vault_session, data):
    """
        Use Vault's Wrapping API to store the signed certificate in exchange
        for a wrap token.
    """
    url = vault_url + "/v1/sys/wrapping/wrap"
    vault_session.headers.update({"X-Vault-Wrap-TTL": DEFAULT_WRAP_TTL})

    response = vault_session.post(url, json=data).json()

    try:
        token = response["wrap_info"]["token"]
        logging.info("wrapped signed public key")

        return token
    except KeyError:
        errors = response.get("errors", [])
        raise Exception("Wrapping failed.  " + "; ".join(errors))
