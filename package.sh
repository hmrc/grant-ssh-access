#!/bin/bash

set -xeou
yum install -y zip python37

BASEDIR=/data
PIPPACKAGESDIR=${BASEDIR}/lambda-packages

cd ${BASEDIR}

zip grant_ssh_access.zip grant_ssh_access.py

mkdir -p ${PIPPACKAGESDIR}
pip-3.6 install -t ${PIPPACKAGESDIR} -r requirements.txt
cd ${PIPPACKAGESDIR}
zip -r ../grant_ssh_access.zip .