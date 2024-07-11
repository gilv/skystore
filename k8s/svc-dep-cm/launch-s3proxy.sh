#!/bin/bash

S3PROXY_YAML=$1

: ${S3PROXY_YAML:="s3proxy.yaml"}

kubectl apply -f $S3PROXY_YAML


