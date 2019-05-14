#!/bin/bash

cd "${BASH_SOURCE%/*}" || exit

source ./venv/bin/activate
source ./env.sh

./main.py "$@"
