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

echo "[+] Checking for leastbot.py updates ..."
TMP_PY="${BIN}.tmp"

if curl -fsSL -z "${BIN}" -o "${TMP_PY}" "${RAW_PY}"; then
  if [ -f "${TMP_PY}" ]; then
    mv "${TMP_PY}" "${BIN}"
    chmod +x "${BIN}"
    echo "[✓] leastbot.py installed/updated."
  else
    chmod +x "${BIN}" 2>/dev/null || true
    echo "[=] leastbot.py already up to date."
  fi
else
  echo "[!] Could not download leastbot.py update. Keeping existing version (if any)."
  rm -f "${TMP_PY}" 2>/dev/null || true
fi


mkdir -p "${CACHE_DIR}"
if [ ! -f "${CACHE_INSTALL}" ]; then

  cp -f "$0" "${CACHE_INSTALL}" 2>/dev/null || true
fi


echo "[+] Installing launcher: ${LAUNCHER}"

cat > "${LAUNCHER}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

REPO="mobin-shahhoseini/leastBOT"
BRANCH="main"
URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}/install.sh"

CACHE_DIR="/var/cache/leastbot"
CACHE_SH="${CACHE_DIR}/install.sh"
BIN="/usr/local/bin/leastbot"

mkdir -p "$CACHE_DIR"

run_install() {
  if [ -f "$CACHE_SH" ]; then
    bash "$CACHE_SH"
  else
    echo "[-] No cached install.sh available."
    exit 1
  fi
}

# If leastbot not installed -> download installer and install, then run leastbot
if [ ! -x "$BIN" ]; then
  echo "[+] leastbot not found. Installing..."
  curl -fsSL -o "$CACHE_SH" "$URL"
  chmod +x "$CACHE_SH"
  run_install
  exec "$BIN"
fi

UPDATED="0"

# If cache missing, fetch once (so we can use -z afterwards)
if [ ! -f "$CACHE_SH" ]; then
  curl -fsSL -o "$CACHE_SH" "$URL"
  chmod +x "$CACHE_SH"
  UPDATED="1"
else
  # Update only if newer
  if curl -fsSL -z "$CACHE_SH" -o "${CACHE_SH}.tmp" "$URL"; then
    if [ -f "${CACHE_SH}.tmp" ]; then
      mv "${CACHE_SH}.tmp" "$CACHE_SH"
      chmod +x "$CACHE_SH"
      UPDATED="1"
      echo "[✓] install.sh updated."
    fi
  else
    rm -f "${CACHE_SH}.tmp" 2>/dev/null || true
    echo "[!] Could not check update (using cached version)."
  fi
fi

# If updated -> run installer to refresh leastbot.py, deps, etc.
if [ "$UPDATED" = "1" ]; then
  echo "[+] Running installer (because updated)..."
  run_install
fi

echo "[+] Running leastbot..."
exec "$BIN"
EOF

chmod +x "${LAUNCHER}"

echo
echo "[✓] Done!"
echo "[*] Run bot: leastbot"
echo "[*] Next time (recommended): leastbot-install  (runs bot, updates only if needed)"
