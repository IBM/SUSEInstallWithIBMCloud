#!/bin/bash

THIS_DIR="$(dirname $0)"

PYTHON="$(which python)"
[ $? -ne 0 ] && echo -e "\nERROR: python not found.\n" && exit 1

PY_SCRIPT="${THIS_DIR}/py/setup_and_config_host.py"
[ ! -f "${PY_SCRIPT}" ] && echo -e "\nERROR: cannot find: ${PY_SCRIPT}" && exit 1

export PROG_NAME="$0"
${PYTHON} ${PY_SCRIPT} $*
