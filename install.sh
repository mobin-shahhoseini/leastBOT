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

echo "[+] Installing dependencies ..."
apt update -y
apt install -y python3 curl openssh-client autossh iproute2

echo "[+] Checking for leastBOT updates ..."

TMP_FILE="${BIN}.tmp"

if curl -fsSL -z "${BIN}" -o "${TMP_FILE}" "${RAW}"; then
    if [ -f "${TMP_FILE}" ]; then
        mv "${TMP_FILE}" "${BIN}"
        chmod +x "${BIN}"
        echo "[✓] leastBOT installed/updated successfully."
    fi
else
    echo "[!] Could not download update. Keeping existing version (if any)."
fi

echo
echo "[✓] Done!"
echo "[*] Run: leastbot"
