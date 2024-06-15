#!/bin/bash

rm -fr keys
mkdir keys
ssh-keygen -b 2048 -t rsa -f keys/skystore -q -N ""
