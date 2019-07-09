import json
import re
from unittest.mock import MagicMock

import boto3
import hvac
import pytest
import responses

import grant_ssh_access


@pytest.fixture(autouse=True)
def default_environment(monkeypatch):
    monkeypatch.setenv("VAULT_URL", "https://vault.okay")


@pytest.fixture(autouse=True)
def mocked_boto3(monkeypatch):
    bizarro_boto3 = MagicMock(spec=boto3)

    bizarro_boto3.Session.return_value.get_credentials.return_value.get_frozen_credentials.return_value.access_key = (  # noqa: E501 line too long
        "x" * 16
    )

    monkeypatch.setattr("grant_ssh_access.boto3", bizarro_boto3)


@pytest.fixture(autouse=True)
def mocked_hvac(monkeypatch):
    bizarro_hvac = MagicMock(spec=hvac)
    bizarro_hvac.Client.return_value.lookup_token.return_value = {
        "data": {"id": "x" * 16}
    }
    monkeypatch.setattr("grant_ssh_access.hvac", bizarro_hvac)


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock() as rsps:
        yield rsps


def test_happy_path(mocked_responses):

    mocked_responses.add(
        mocked_responses.POST,
        url=re.compile(r".*/v1/ssh-platsec-poc/sign/signer-poc"),
        body=json.dumps({"data": {"some": "data"}}),
    )

    mocked_responses.add(
        mocked_responses.POST,
        url=re.compile(r".*/v1/sys/wrapping/wrap"),
        body=json.dumps({"wrap_info": {"token": "token"}}),
    )

    response = grant_ssh_access.main("", "", "")
    assert "token" in response


def test_bad_sign_certificate_response(mocked_responses):
    mocked_responses.add(
        mocked_responses.POST,
        url=re.compile(r".*/v1/ssh-platsec-poc/sign/signer-poc"),
        body=json.dumps({"bad": {}}),
    )

    response = grant_ssh_access.main("", "", "")
    assert "error" in response


def test_bad_wrapping_response(mocked_responses):
    mocked_responses.add(
        mocked_responses.POST,
        url=re.compile(r".*/v1/ssh-platsec-poc/sign/signer-poc"),
        body=json.dumps({"data": {"some": "data"}}),
    )

    mocked_responses.add(
        mocked_responses.POST,
        url=re.compile(r".*/v1/sys/wrapping/wrap"),
        body=json.dumps({"bad": {}}),
    )

    response = grant_ssh_access.main("", "", "")
    assert "error" in response


@pytest.fixture
def bad_boto3(monkeypatch):
    boto_bad_creds = MagicMock(spec=boto3)

    boto_bad_creds.Session.return_value.get_credentials.return_value.get_frozen_credentials.return_value = (  # noqa: E501 line too long
        None
    )

    monkeypatch.setattr("grant_ssh_access.boto3", boto_bad_creds)


def test_bad_aws_credentials(bad_boto3):
    response = grant_ssh_access.main("", "", "")
    assert "error" in response
