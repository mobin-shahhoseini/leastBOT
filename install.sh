#!/usr/bin/env bash
set -e

APP="leastBOT"
BIN="/usr/local/bin/leastbot"

REPO="mobin-shahhoseini/leastBOT"
BRANCH="main"
RAW_PY="https://raw.githubusercontent.com/${REPO}/${BRANCH}/leastbot.py"
RAW_INSTALL="https://raw.githubusercontent.com/${REPO}/${BRANCH}/install.sh"

LAUNCHER="/usr/local/bin/leastbot-install"
CACHE_DIR="/var/cache/leastbot"
CACHE_INSTALL="${CACHE_DIR}/install.sh"

echo "[+] Installing ${APP} ..."

if [ "$(id -u)" -ne 0 ]; then
  echo "[-] Please run as root: sudo -i"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo "[+] Installing dependencies ..."
apt update -y
apt install -y python3 curl openssh-client autossh iproute2

# -------------------------
# 1) Install/update leastbot.py (only if newer)
# -------------------------
echo "[+] Checking for leastbot.py updates ..."
TMP_PY="${BIN}.tmp"

if curl -fsSL -z "${BIN}" -o "${TMP_PY}" "${RAW_PY}"; then
  if [ -f "${TMP_PY}" ]; then
    mv "${TMP_PY}" "${BIN}"
    chmod +x "${BIN}"
    echo "[✓] leastbot.py installed/updated."
  else
    # Not modified
    chmod +x "${BIN}" 2>/dev/null || true
    echo "[=] leastbot.py already up to date."
  fi
else
  echo "[!] Could not download leastbot.py update. Keeping existing version (if any)."
  rm -f "${TMP_PY}" 2>/dev/null || true
fi


echo "[+] Installing launcher: ${LAUNCHER}"

cat > "${LAUNCHER}" <<EOF
#!/usr/bin/env bash
set -euo pipefail

APP="${APP}"
REPO="${REPO}"
BRANCH="${BRANCH}"
URL="https://raw.githubusercontent.com/\${REPO}/\${BRANCH}/install.sh"

CACHE_DIR="${CACHE_DIR}"
CACHE_SH="${CACHE_INSTALL}"

mkdir -p "\${CACHE_DIR}"

echo "[+] \${APP} launcher started..."

# First-time download
if [ ! -f "\${CACHE_SH}" ]; then
  echo "[+] First time download of install.sh..."
  curl -fsSL -o "\${CACHE_SH}" "\${URL}"
  chmod +x "\${CACHE_SH}"
fi

# Update only if newer (no useless downloads)
if curl -fsSL -z "\${CACHE_SH}" -o "\${CACHE_SH}.tmp" "\${URL}"; then
  if [ -f "\${CACHE_SH}.tmp" ]; then
    mv "\${CACHE_SH}.tmp" "\${CACHE_SH}"
    chmod +x "\${CACHE_SH}"
    echo "[✓] install.sh updated."
  fi
else
  echo "[!] Could not check for update (using cached version)."
  rm -f "\${CACHE_SH}.tmp" 2>/dev/null || true
fi

exec bash "\${CACHE_SH}"
EOF

chmod +x "${LAUNCHER}"

echo
echo "[✓] Done!"
echo "[*] Run bot: leastbot"
echo "[*] Next time update/install (without re-downloading install.sh): leastbot-install"
