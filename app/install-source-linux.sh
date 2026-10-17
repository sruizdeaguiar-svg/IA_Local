#!/bin/sh
set -eu
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$src/app/install_portable_source.py" --destination "${1:-$HOME/.local/opt/ia-local}" --data "${2:-${XDG_DATA_HOME:-$HOME/.local/share}/IA-Local}" --desktop
