#!/bin/sh
# Self-extracting installer: payload integrity is checked before executing it.
set -eu
umask 077
installer_temp=$(mktemp -d "${TMPDIR:-/tmp}/fgts-guias-install.XXXXXXXX")
trap 'rm -rf "$installer_temp"' EXIT HUP INT TERM
payload_line=$(awk '/^__FGTS_PAYLOAD__$/ {print NR + 1; exit}' "$0")
tail -n +"$payload_line" "$0" > "$installer_temp/payload.tar.gz"
printf '%s  %s\n' '@PAYLOAD_SHA256@' "$installer_temp/payload.tar.gz" | sha256sum -c - >/dev/null
tar -xzf "$installer_temp/payload.tar.gz" -C "$installer_temp"
"$installer_temp/@PACKAGE_NAME@/fgts_guias" --install
exit $?
__FGTS_PAYLOAD__
