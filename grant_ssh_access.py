#!/usr/bin/env python3
import os
import traceback
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
    region = os.getenv('REGION')
    vault_url = os.getenv('VAULT_URL')
    public_key = "ssh-rsa some public key"
    name = "user name"
    ttl = "21600"
    region = "eu-west-2"
    credentials = _get_aws_credentials()
    client = _connect_to_vault(vault_url, credentials.access_key, credentials.secret_key, credentials.token, region)
    current_token = client.lookup_token()
    current_json = json.loads(json.dumps(current_token))
    vault_token = (current_json['data']['id'])
    vault_sign_certificate(vault_url, name, public_key, ttl, vault_token)

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
        vault_client = hvac.Client(url=url, verify=False)
    else:
        vault_client = hvac.Client(url=url, verify=False)

    vault_client.auth_aws_iam(access_key,
                              secret_key,
                              token,
                              region=region)

    return vault_client

def vault_sign_certificate(vault_url, user_name, public_key, ttl, vault_token):
    print("###### Signing Public Certificate ######")
    url = vault_url + "/v1/ssh-platsec-poc/sign/signer-poc"
    data = {
        "public_key": public_key,
        "valid_principals": user_name,
        "ttl": ttl,
    }
    headers = {"X-Vault-Token": vault_token}

    response = requests.post(url, json=data, headers=headers, verify=False)
    print(response.content)

    # try:
    #     return response["data"]
    # except KeyError:
    #     errors = response.get("errors", [])
    #     raise Exception("Certificate signing failed.  " + "; ".join(errors))


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
