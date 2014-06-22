#!/bin/bash

[ $# -ne 1 ] && echo "Usage: $0 <devid>" && exit

DEVID="$1"

cat <<EOF > ./envsetup.sh
export DEVID="$DEVID"
export PDPATH="`pwd`"
export PYTHONPATH="`pwd`"
EOF

echo "Environment variables setup in envsetup.sh, please call 'source envsetup.sh' before using Paradrop tools"

