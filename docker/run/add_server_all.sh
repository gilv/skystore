#!/bin/bash

../add_server_env_pub_key.sh env.base
mv env.base.withpubkey env.final
rm -f *with*

