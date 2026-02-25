#!/usr/bin/env bash
set -e

APP="leastBOT"
BIN="/usr/local/bin/leastbot"
REPO="leastping/leastBOT"
RAW="https://raw.githubusercontent.com/${REPO}/main/leastbot.py"

echo "[+] Installing ${APP} ..."

if [ "$(id -u)" -ne 0 ]; then
  echo "[-] Please run as root: sudo -i"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt update -y
apt install -y python3 curl openssh-client autossh iproute2

echo "[+] Downloading script ..."
curl -fsSL "${RAW}" -o "${BIN}"

chmod +x "${BIN}"

echo
echo "[✓] Done!"
echo "[*] Run: leastbot"
echo