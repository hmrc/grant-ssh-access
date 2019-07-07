#!/usr/bin/env python3
import os
import traceback
import aws_get_vault_object
import requests
import hvac
import boto3
import json

class State:
    def __init__(self):
        self.ENVIRONMENT = os.environ["ENVIRONMENT"].lower()
        self.VAULT_URL = "https://vault.tools.{}.tax.service.gov.uk".format(
            self.ENVIRONMENT
        )
        self.VAULT_ROLE_ID = os.environ["VAULT_ROLE_ID"]
        self.VAULT_SECRET_ID = os.environ["VAULT_SECRET_ID"]
        self.DEFAULT_WRAP_TTL = str(60 * 60 * 4)

        self.vault_auth_token = None


# def lambda_handler(event, context):
#     return main(event["user_name"], event["public_key"], event["ttl"])

def lambda_handler(event, context):
    # credentials = _get_aws_credentials()
    # print(credentials.token)
    print("wibble")

def _get_aws_credentials():
    """
        Return keys and token for the instances IAM role.
    """
    session = boto3.Session()
    credentials = session.get_credentials()
    credentials = credentials.get_frozen_credentials()

    if not hasattr(credentials, 'access_key'):
        raise BadCredentials

    if len(credentials.access_key) < 16:
        raise BadCredentials

    return credentials


def _connect_to_vault(url, access_key, secret_key, token, region, ca_cert=None):
    """
        Return Vault client using supplied IAM credentials.
    """
    # Add CA_CERT for lambda requests to vault
    if ca_cert:
        vault_client = hvac.Client(url=url, verify=ca_cert)
    else:
        vault_client = hvac.Client(url=url)

    vault_client.auth_aws_iam(access_key,
                              secret_key,
                              token,
                              region=region)

    return vault_client

def lambda_handler(event, context):
    credentials = _get_aws_credentials()
    print(credentials.token)

def main(user_name, public_key, ttl):
    try:
        state = State()

        vault_authenticate(state)
        signed_cert_response = vault_sign_certificate(
            state, user_name, public_key, ttl
        )
        wrapped_token = vault_wrap(state, json_blob=signed_cert_response)

        return {"token": wrapped_token}
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}


def vault_authenticate(state):
    url = state.VAULT_URL + "/v1/auth/approle/login"
    data = {"role_id": state.VAULT_ROLE_ID, "secret_id": state.VAULT_SECRET_ID}

    response = requests.post(url, json=data).json()

    try:
        state.vault_auth_token = response["auth"]["client_token"]
    except KeyError:
        raise Exception(
            "vault authentication failed!  "
            "is the AppRole for this application configured correctly?"
        )


def vault_sign_certificate(state, user_name, public_key, ttl):
    url = (
        state.VAULT_URL
        # TODO Change this to the real ssh backend!
        + "/v1/ssh-platsec-poc/sign/signer-poc"
    )
    data = {
        "public_key": public_key,
        "valid_principals": user_name,
        "ttl": ttl,
    }
    headers = {"X-Vault-Token": state.vault_auth_token}

    response = requests.post(url, json=data, headers=headers).json()

    try:
        return response["data"]
    except KeyError:
        errors = response.get("errors", [])
        raise Exception("Certificate signing failed.  " + "; ".join(errors))


def vault_wrap(state, json_blob):
    url = state.VAULT_URL + "/v1/sys/wrapping/wrap"
    data = json_blob
    headers = {
        "X-Vault-Token": state.vault_auth_token,
        "X-Vault-Wrap-TTL": state.DEFAULT_WRAP_TTL,
    }

    response = requests.post(url, json=data, headers=headers).json()

    try:
        return response["wrap_info"]["token"]
    except KeyError:
        errors = response.get("errors", [])
        raise Exception("Wrapping failed.  " + "; ".join(errors))
