#!/bin/bash
echo "Starting SkyStore S3-Proxy service"
skystore init --config=$1

# S3-proxy is running - wair until it fails or is killed
echo "Waiting for S3-proxy to finish"
skystore proxyjoin
