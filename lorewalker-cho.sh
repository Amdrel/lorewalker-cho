#!/bin/bash

cd "${BASH_SOURCE%/*}" || exit

source ./venv/bin/activate
source ./env.sh

exec ./main.py "$@"
