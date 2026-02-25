#!/usr/bin/env bash
set -e

APP="leastBOT"
BIN="/usr/local/bin/leastbot"

REPO="mobin-shahhoseini/leastBOT"
BRANCH="main"
RAW="https://raw.githubusercontent.com/${REPO}/${BRANCH}/leastbot.py"

echo "[+] Installing ${APP} ..."

if [ "$(id -u)" -ne 0 ]; then
  echo "[-] Please run as root: sudo -i"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt update -y
apt install -y python3 curl openssh-client autossh iproute2

echo "[+] Downloading leastBOT script ..."
curl -fsSL "${RAW}" -o "${BIN}"
chmod +x "${BIN}"

echo
echo "[✓] Done!"
echo "[*] Run: leastbot"
