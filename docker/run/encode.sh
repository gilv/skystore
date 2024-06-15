#!/bin/bash

cat $1 | base64 | tr -d '\n'

