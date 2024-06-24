#!/bin/bash

basepath=$(dirname $0)

cp $1 $1.withpubkey
echo "SKYSTORE_PUB_KEY="$($basepath/encode.sh keys/skystore.pub) >> $1.withpubkey
 
