import botocore.session
from botocore.awsrequest import create_request_object
import json
import base64
import sys
from botocore.vendored import requests

def headers_to_go_style(headers):
    retval = {}
    for k, v in headers.iteritems():
        retval[k] = [v]
    return retval

def generate_vault_request(awsIamServerId):
    print("checkpoint1")
    session = botocore.session.get_session()
    client = session.create_client('sts')
    endpoint = client._endpoint
    operation_model = client._service_model.operation_model('GetCallerIdentity')
    request_dict = client._convert_to_request_dict({}, operation_model)
    request_dict['headers']['X-Vault-AWS-IAM-Server-ID'] = awsIamServerId
    request = endpoint.create_request(request_dict, operation_model)
    return {
        'role':                 "grant-ssh-policy",
        'iam_http_request_method': request.method,
        'iam_request_url':         base64.b64encode(request.url),
        'iam_request_body':        base64.b64encode(request.body),
        'iam_request_headers':     base64.b64encode(json.dumps(headers_to_go_style(dict(request.headers)))), # It's a CaseInsensitiveDict, which is not JSON-serializable
    }

def lambda_handler(event, context):
    awsIamServerId = ""
    signed_request = json.dumps(generate_vault_request(awsIamServerId))
    print(signed_request)

    data=json.loads(signed_request)
    print(data)
    url = "https://vault.integration.mdtp:8200/v1/auth/aws/login"
    response = requests.post(url, json=data, verify=False)
    print(response.json())

# Look at the bottom half of this to work out how it all works: https://www.vaultproject.io/docs/auth/aws.html
