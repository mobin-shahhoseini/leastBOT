#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
leastBOT - Reverse SSH Tunnel Manager (autossh + systemd)
Developer: @leastping | mobin-shahhoseini
Updates only in Telegram: https://t.me/leastping

Scenario (SIMPLE - exactly like your steps):
- KHAREJ: enable AllowTcpForwarding + GatewayPorts, open PORT
- IRAN : autossh reverse tunnel (IRAN:PORT -> KHAREJ:PORT public)
Goal: http://IP_KHAREJ:PORT/

Notes:
- Beautiful UI (logo/spinner/colors/emojis)
- Daily auto update check (GitHub raw)
- NO extra options (no bind choice, no separate local/remote ports)
- NO Persian script in messages (Finglish only)
"""

import os
import re
import sys
import time
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlopen, Request

# =========================
# App / Repo
# =========================
__app__ = "leastBOT"
__version__ = "1.1.1"

GITHUB_REPO = "mobin-shahhoseini/leastBOT"
BRANCH = "main"
RAW_MAIN_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{BRANCH}/leastbot.py"

SERVICE_DIR = "/etc/systemd/system"
SERVICE_NAME = "reverse-tunnel.service"
SERVICE_PATH = f"{SERVICE_DIR}/{SERVICE_NAME}"

CACHE_DIR = Path("/var/lib/leastbot")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ANSI = {
    "reset": "\033[0m",
    "green": "\033[92m",
    "red": "\033[91m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
    "bold": "\033[1m",
    "dim": "\033[2m",
}

def c(text, color):
    return f"{ANSI.get(color,'')}{text}{ANSI['reset']}"

LOGO = rf"""
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   ██╗      ███████╗ █████╗ ███████╗████████╗██████╗  ██████╗ ████████╗       │
│   ██║      ██╔════╝██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗╚══██╔══╝       │
│   ██║      █████╗  ███████║███████╗   ██║   ██████╔╝██║   ██║   ██║          │
│   ██║      ██╔══╝  ██╔══██║╚════██║   ██║   ██╔══██╗██║   ██║   ██║          │
│   ███████╗ ███████╗██║  ██║███████║   ██║   ██████╔╝╚██████╔╝   ██║          │
│   ╚══════╝ ╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═════╝  ╚═════╝    ╚═╝          │
│                                                                              │
│            leastBOT • Reverse SSH Tunnel Manager • v{__version__:<8}          │
│            Iran <-> Kharj  (autossh + systemd)                               │
│                                                                              │
│            Developer: @leastping                                             │
│            Updates only in Telegram: https://t.me/leastping                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
"""

# =========================
# Utils
# =========================
def clear():
    os.system("clear" if os.name != "nt" else "cls")

def spinner(msg="Loading", seconds=0.9):
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    end = time.time() + seconds
    i = 0
    while time.time() < end:
        sys.stdout.write("\r" + c(f"{frames[i%len(frames)]} {msg}...", "cyan"))
        sys.stdout.flush()
        time.sleep(0.07)
        i += 1
    sys.stdout.write("\r" + c(f"✓ {msg} done.      ", "green") + "\n")

def run(cmd, check=True, capture=False):
    print(c(f"\n$ {cmd}", "cyan"))
    if capture:
        res = subprocess.run(
            cmd, shell=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        out = res.stdout or ""
        if check and res.returncode != 0:
            raise subprocess.CalledProcessError(res.returncode, cmd, output=out)
        return out
    res = subprocess.run(cmd, shell=True)
    if check and res.returncode != 0:
        raise subprocess.CalledProcessError(res.returncode, cmd)
    return ""

def is_root():
    try:
        return os.geteuid() == 0
    except Exception:
        return False

def ask(prompt, default=None, validator=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        try:
            s = input(c(f"{prompt}{suffix}: ", "bold")).strip()
        except KeyboardInterrupt:
            print(c("\n^C Cancelled.", "yellow"))
            return ""
        if not s and default is not None:
            s = str(default)
        if validator and s:
            ok, msg = validator(s)
            if not ok:
                print(c(f"✗ {msg}", "red"))
                continue
        return s

def valid_ip(s):
    parts = s.split(".")
    if len(parts) != 4:
        return False, "IP na-motabar ast."
    try:
        nums = [int(p) for p in parts]
    except Exception:
        return False, "IP na-motabar ast."
    if any(n < 0 or n > 255 for n in nums):
        return False, "IP na-motabar ast."
    return True, ""

def valid_port(s):
    if not s.isdigit():
        return False, "Port bayad adad bashad."
    p = int(s)
    if p < 1 or p > 65535:
        return False, "Port bayad beyn 1 ta 65535 bashad."
    return True, ""

def yesno(s: str) -> bool:
    return str(s).strip().lower().startswith("y")

# =========================
# Auto Update (daily)
# =========================
def parse_version(v):
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except Exception:
        return (0, 0, 0)

def fetch_url_text(url, timeout=12):
    req = Request(url, headers={"User-Agent": f"{__app__}/{__version__}"})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")

def can_check_updates_daily():
    stamp = CACHE_DIR / "last_update_check.txt"
    now = int(time.time())
    if not stamp.exists():
        return True
    try:
        last = int(stamp.read_text().strip())
        return (now - last) > 86400
    except Exception:
        return True

def mark_checked():
    (CACHE_DIR / "last_update_check.txt").write_text(str(int(time.time())))

def self_update(force=False):
    try:
        if not force and not can_check_updates_daily():
            return

        txt = fetch_url_text(RAW_MAIN_URL, timeout=12)
        mark_checked()

        m = re.search(r'__version__\s*=\s*"([^"]+)"', txt)
        if not m:
            return
        remote_ver = m.group(1).strip()

        if not force and parse_version(remote_ver) <= parse_version(__version__):
            print(c(f"✓ Update: no new version. (local={__version__}, remote={remote_ver})", "dim"))
            return

        print(c(f"🆕 New version: {remote_ver} (local={__version__})", "yellow"))
        if not yesno(ask("Update now? (y/n)", default="y" if force else "n")):
            print(c("Update cancelled.", "yellow"))
            return

        installed_path = Path("/usr/local/bin/leastbot")
        script_path = installed_path if installed_path.exists() else Path(sys.argv[0]).resolve()
        if not script_path.exists():
            print(c("! Script path not found.", "red"))
            return

        backup = script_path.with_suffix(script_path.suffix + ".bak")
        shutil.copy2(script_path, backup)

        tmp = script_path.with_suffix(".tmp")
        tmp.write_text(txt, encoding="utf-8")
        tmp.chmod(script_path.stat().st_mode)
        tmp.replace(script_path)

        print(c(f"✅ Updated. Backup: {backup}", "green"))
        print(c("Restart script to load new version.", "cyan"))
        sys.exit(0)

    except Exception as e:
        print(c(f"! Update error: {e}", "yellow"))

# =========================
# Install helpers
# =========================
def ensure_cmd(cmd_name, apt_pkg=None):
    if shutil.which(cmd_name):
        return
    pkg = apt_pkg or cmd_name
    print(c(f"📦 '{cmd_name}' not found, installing: {pkg}", "yellow"))
    run("apt update")
    run(f"apt install -y {pkg}")

def ensure_basics_iran():
    ensure_cmd("ssh", "openssh-client")
    ensure_cmd("ssh-keygen", "openssh-client")
    ensure_cmd("ssh-copy-id", "openssh-client")
    ensure_cmd("autossh", "autossh")
    ensure_cmd("ss", "iproute2")

def ensure_basics_kharj():
    ensure_cmd("ss", "iproute2")
    if not shutil.which("sshd"):
        print(c("⚠ sshd not found, installing openssh-server...", "yellow"))
        run("apt update")
        run("apt install -y openssh-server")

def ensure_key():
    key_path = Path("/root/.ssh/id_ed25519")
    pub_path = Path("/root/.ssh/id_ed25519.pub")
    key_dir = Path("/root/.ssh")
    key_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(str(key_dir), 0o700)

    if key_path.exists() and pub_path.exists():
        print(c("🔑 SSH key exists: /root/.ssh/id_ed25519", "green"))
        return

    print(c("🔑 Creating SSH key (ed25519)...", "yellow"))
    run('ssh-keygen -t ed25519 -N "" -f /root/.ssh/id_ed25519')

def ssh_copy_id(user, host, ssh_port):
    print(c("🔐 Sending key to KHAREJ (password needed)...", "yellow"))
    run(f"ssh-copy-id -p {ssh_port} {user}@{host}", check=True)

def test_ssh(user, host, ssh_port):
    out = run(
        f'ssh -p {ssh_port} -o StrictHostKeyChecking=accept-new {user}@{host} "echo OK"',
        capture=True,
        check=False,
    ) or ""
    return "OK" in out

# =========================
# Robust remote port check
# =========================
def remote_port_is_free(user, host, ssh_port, port: int) -> bool:
    cmd = (
        f'ssh -p {ssh_port} -o StrictHostKeyChecking=accept-new {user}@{host} '
        f'"ss -H -lnt \\"sport = :{port}\\" | wc -l"'
    )
    out = run(cmd, capture=True, check=False).strip()
    try:
        return int(out) == 0
    except Exception:
        return False

# =========================
# Firewall + sshd config on KHAREJ
# =========================
def detect_firewall():
    if shutil.which("ufw"):
        out = run("ufw status", capture=True, check=False) or ""
        if "Status: active" in out:
            return "ufw"
    if shutil.which("firewall-cmd"):
        out = run("systemctl is-active firewalld", capture=True, check=False) or ""
        if out.strip() == "active":
            return "firewalld"
    if shutil.which("iptables"):
        return "iptables"
    return "none"

def open_port(port: int):
    fw = detect_firewall()
    print(c(f"🧱 Firewall: {fw}", "yellow"))
    if fw == "ufw":
        run(f"ufw allow {port}/tcp", check=False)
    elif fw == "firewalld":
        run(f"firewall-cmd --add-port={port}/tcp --permanent", check=False)
        run("firewall-cmd --reload", check=False)
    elif fw == "iptables":
        run(
            f"iptables -C INPUT -p tcp --dport {port} -j ACCEPT || "
            f"iptables -A INPUT -p tcp --dport {port} -j ACCEPT",
            check=False,
        )
        print(c("⚠ iptables rule added (may be lost after reboot).", "yellow"))
    else:
        print(c("⚠ No firewall tool detected. Check provider firewall too.", "yellow"))

def ensure_sshd_config_safe():
    path = "/etc/ssh/sshd_config"
    if not os.path.exists(path):
        raise RuntimeError("File /etc/ssh/sshd_config not found.")

    backup = path + ".leastbot.bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
        print(c(f"🧷 Backup created: {backup}", "green"))

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    def set_or_add(key, value):
        pattern = re.compile(rf"^\s*#?\s*{re.escape(key)}\s+.*$", re.IGNORECASE)
        for i, line in enumerate(lines):
            if pattern.match(line):
                lines[i] = f"{key} {value}\n"
                return
        lines.append(f"\n{key} {value}\n")

    set_or_add("AllowTcpForwarding", "yes")
    set_or_add("GatewayPorts", "yes")

    tmp = path + ".leastbot.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(lines)

    sshd_bin = shutil.which("sshd") or "/usr/sbin/sshd"
    test_out = run(f"{sshd_bin} -t -f {tmp} && echo OK || echo FAIL", capture=True, check=False).strip()
    if "OK" not in test_out:
        try:
            os.remove(tmp)
        except Exception:
            pass
        raise RuntimeError("sshd_config validation failed (sshd -t). No changes applied.")

    shutil.copy2(tmp, path)
    os.remove(tmp)
    print(c("✅ sshd_config updated: AllowTcpForwarding/GatewayPorts", "green"))

def restart_ssh():
    run("systemctl restart ssh", check=False)
    run("systemctl restart sshd", check=False)

# =========================
# Systemd service on IRAN (FIXED)
# =========================
def systemd_verify_unit(path: str) -> bool:
    # Optional verification; if systemd-analyze exists, validate unit syntax.
    if not shutil.which("systemd-analyze"):
        return True
    out = run(f"systemd-analyze verify {path} 2>&1 || true", capture=True, check=False)
    # systemd-analyze prints nothing on success in many cases; treat "Failed" as bad.
    if "Failed to" in out or "error" in out.lower():
        print(c("⚠ systemd-analyze verify reported issues:", "yellow"))
        print(out.strip())
        return False
    return True

def write_reverse_service(remote_user, remote_ip, ssh_port, port: int):
    autossh_path = shutil.which("autossh") or "/usr/bin/autossh"

    content = (
        "[Unit]\n"
        f"Description=Reverse SSH Tunnel IR -> KHAREJ ({port})\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n"
        "StartLimitIntervalSec=0\n\n"
        "[Service]\n"
        "Type=simple\n"
        "User=root\n"
        'Environment="AUTOSSH_GATETIME=0"\n'
        f"ExecStart={autossh_path} -M 0 -N \\\n"
        "  -o ServerAliveInterval=30 \\\n"
        "  -o ServerAliveCountMax=3 \\\n"
        "  -o ExitOnForwardFailure=yes \\\n"
        "  -o StrictHostKeyChecking=accept-new \\\n"
        f"  -p {ssh_port} \\\n"
        f"  -R 0.0.0.0:{port}:127.0.0.1:{port} \\\n"
        f"  {remote_user}@{remote_ip}\n"
        "Restart=always\n"
        "RestartSec=5\n\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )

    tmp_path = SERVICE_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Validate unit syntax BEFORE replacing the real file
    if not systemd_verify_unit(tmp_path):
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        raise RuntimeError("Unit file validation failed. Service file not applied.")

    # Backup old service if exists
    if os.path.exists(SERVICE_PATH):
        bkp = SERVICE_PATH + ".bak"
        try:
            shutil.copy2(SERVICE_PATH, bkp)
        except Exception:
            pass

    os.replace(tmp_path, SERVICE_PATH)

def enable_start_service():
    run("systemctl daemon-reload")
    run(f"systemctl enable --now {SERVICE_NAME}")
    run(f"systemctl status {SERVICE_NAME} --no-pager", check=False)

def remove_service():
    run(f"systemctl disable --now {SERVICE_NAME}", check=False)
    if os.path.exists(SERVICE_PATH):
        os.remove(SERVICE_PATH)
        print(c(f"🧹 Removed: {SERVICE_PATH}", "green"))
    run("systemctl daemon-reload")

# =========================
# Modes (simple)
# =========================
def print_main_menu():
    print(c("\nMain Menu", "bold"))
    print(c("0) Exit", "dim"))
    print("1) Iran  (Client)  [Create Reverse Tunnel Service]")
    print("2) Kharj (Server)  [Enable forwarding + open port]")
    print("3) Status / Logs")
    print("4) Remove Tunnel Service (Iran)")
    print("5) Check / Update (GitHub)")

def mode_kharj():
    print(c("\n=== MODE: KHAREJ (Server) ===", "bold"))
    port = ask("Port to open on KHAREJ (mesal: 2087)", validator=valid_port)
    if not port:
        return

    ensure_basics_kharj()
    ensure_sshd_config_safe()
    restart_ssh()
    open_port(int(port))

    print(c("\n✅ Done! Now go to IRAN and create the tunnel.", "green"))
    print(c("Note: Port will LISTEN only after tunnel is up.", "dim"))

def mode_iran():
    print(c("\n=== MODE: IRAN (Client) ===", "bold"))
    port = ask("Panel port (IRAN=KHAREJ same) (mesal: 2087)", validator=valid_port)
    if not port:
        return
    remote_ip = ask("IP server KHAREJ", validator=valid_ip)
    if not remote_ip:
        return
    remote_user = ask("SSH user on KHAREJ", default="root")
    if not remote_user:
        return
    ssh_port = ask("SSH port on KHAREJ", default="22", validator=valid_port)
    if not ssh_port:
        return

    ensure_basics_iran()
    ensure_key()

    print(c("\n🔁 Sending key...", "yellow"))
    ssh_copy_id(remote_user, remote_ip, ssh_port)

    print(c("🧪 Testing SSH ...", "yellow"))
    if not test_ssh(remote_user, remote_ip, ssh_port):
        print(c("✗ SSH test failed. Fix SSH then retry.", "red"))
        return

    print(c("🔍 Checking remote port availability ...", "yellow"))
    if not remote_port_is_free(remote_user, remote_ip, ssh_port, int(port)):
        print(c(f"✗ Remote port {port} is already in use on KHAREJ.", "red"))
        print(c("Free the port or choose another port.", "yellow"))
        return

    print(c("🧩 Writing systemd service ...", "yellow"))
    try:
        write_reverse_service(remote_user, remote_ip, ssh_port, int(port))
    except Exception as e:
        print(c(f"✗ Service write failed: {e}", "red"))
        return

    print(c("🚀 Enabling & starting service ...", "yellow"))
    enable_start_service()

    print(c("\n✅ Done!", "green"))
    # IMPORTANT: final output ONLY IP:PORT
    print(c(f"{remote_ip}:{port}", "cyan"))

def mode_status_logs():
    print(c("\n=== STATUS / LOGS ===", "bold"))
    run(f"systemctl status {SERVICE_NAME} --no-pager", check=False)
    run(f"journalctl -u {SERVICE_NAME} -n 200 --no-pager", check=False)

# =========================
# Main
# =========================
def main():
    try:
        clear()
        print(LOGO)

        if not is_root():
            print(c("✗ Run as root: sudo -i", "red"))
            return

        spinner("Starting leastBOT", seconds=0.9)

        print(c("Checking updates (daily)...", "dim"))
        self_update(force=False)

        while True:
            print_main_menu()
            try:
                choice = input(c("\nSelect option [0-5]: ", "bold")).strip()
            except KeyboardInterrupt:
                print(c("\nBye 👋  Updates: https://t.me/leastping\n", "cyan"))
                break

            if choice == "0":
                print(c("\nBye 👋  Updates: https://t.me/leastping\n", "cyan"))
                break
            elif choice == "1":
                mode_iran()
            elif choice == "2":
                mode_kharj()
            elif choice == "3":
                mode_status_logs()
            elif choice == "4":
                confirm = ask("Are you sure to remove reverse-tunnel service? (y/n)", default="n")
                if confirm and yesno(confirm):
                    remove_service()
                    print(c("✅ Removed.", "green"))
                else:
                    print(c("Canceled.", "yellow"))
            elif choice == "5":
                print(c("\n=== UPDATE (GitHub) ===", "bold"))
                self_update(force=True)
            else:
                print(c("✗ Invalid option.", "red"))

            try:
                input(c("\nEnter to back menu ...", "yellow"))
            except KeyboardInterrupt:
                print(c("\nBye 👋  Updates: https://t.me/leastping\n", "cyan"))
                break
            clear()
            print(LOGO)

    except KeyboardInterrupt:
        print(c("\nBye 👋  Updates: https://t.me/leastping\n", "cyan"))

if __name__ == "__main__":
    main()
