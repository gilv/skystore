#!/bin/bash

# First arg is env file, second arg is AWS S3 config file
cp $1 $1.withs3cfg
echo "S3_CFG="$(./encode.sh $2) >> $1.withs3cfg

