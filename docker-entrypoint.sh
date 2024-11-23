#!/bin/bash

# shellcheck disable=SC2164
cd /workspace
exec python main.py "$@"
