#!/bin/bash

aws-profile -p deity \
    aws lambda \
    update-function-code \
    --function-name arn:aws:lambda:eu-west-2:150648916438:function:grant-ssh-access \
    --zip-file fileb://grant_ssh_access.zip


