#!/bin/sh
# Per-user installation. First argument optionally selects the application folder.
set -eu
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
dest=${1:-"$HOME/.local/opt/ia-local"}
case "$dest" in /*) ;; *) echo 'Choose an absolute application directory.' >&2; exit 1;; esac
if [ -e "$dest/IA-Local" ]; then echo 'An installation already exists; choose another directory.' >&2; exit 1; fi
mkdir -p -- "$dest"
cp -- "$src/IA-Local" "$dest/IA-Local"
cp -- "$src/icon-512.png" "$dest/icon-512.png"
chmod 755 "$dest/IA-Local"
# Escape desktop entry values; reject control characters rather than generating commands.
case "$dest" in *'"'*|*'`'*|*'$'*|*'\'*|*'
'*) echo "Installed. Create a desktop launcher manually for this path: $dest"; exit 0;; esac
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/ia-local.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=IA Local
Comment=Local AI services and model manager
Exec="$dest/IA-Local"
Icon=$dest/icon-512.png
Terminal=false
Categories=Utility;Development;
EOF
printf 'Installed: %s\nChoose a data directory with: "%s/IA-Local" --data /absolute/path\n' "$dest" "$dest"
