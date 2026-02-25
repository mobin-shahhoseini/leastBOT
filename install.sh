#!/usr/bin/env bash
set -e

APP="leastBOT"
BIN="/usr/local/bin/leastbot"

REPO="mobin-shahhoseini/leastBOT"
BRANCH="main"
RAW_PY="https://raw.githubusercontent.com/${REPO}/${BRANCH}/leastbot.py"

need_cmd() { command -v "$1" >/dev/null 2>&1; }

install_deps_if_missing() {
  local missing=0
  for c in python3 curl ssh autossh ss; do
    if ! need_cmd "$c"; then
      missing=1
      break
    fi
  done

  if [ "$missing" = "1" ]; then
    export DEBIAN_FRONTEND=noninteractive
    apt update -y
    apt install -y python3 curl openssh-client autossh iproute2
  fi
}

download_leastbot_if_missing() {
  if [ ! -x "$BIN" ]; then
    curl -fsSL "$RAW_PY" -o "$BIN"
    chmod +x "$BIN"
  fi
}

if [ "$(id -u)" -ne 0 ]; then
  echo "[-] Please run as root: sudo -i"
  exit 1
fi


install_deps_if_missing


download_leastbot_if_missing

exec "$BIN"
