
# grant-ssh-access

This is a lambda that takes a username and public key, and:
- Signs the public key using Vault.
- Wraps the signed public key using Vault's Wrapping service.
- Returns the wrapping token back to the caller.

## Configuration

#### Required Vault permissions
```
"path "ssh-platsec-poc/sign/signer-poc" {
  capabilities = ["create", "update"]
}

path "sys/wrapping/wrap" {
  capabilities = ["create"]
}
```

#### Environment variables
- `ENVIRONMENT` - `development`/`integration`/`qa`/`externaltest`/`production`
- `VAULT_ROLE_ID` - AppRole ID
-  `VAULT_SECRET_ID` - AppRole secret

### License

This code is open source software licensed under the [Apache 2.0 License]("http://www.apache.org/licenses/LICENSE-2.0.html").
