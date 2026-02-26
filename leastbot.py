#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
leastBOT - Reverse SSH Tunnel Manager (autossh + systemd)
Developer: @leastping | mobin-shahhoseini
Updates: https://t.me/leastping

Scenario:
- Kharj = Public server (entry)
- Iran  = Client (creates reverse ssh tunnel to Kharj)

OS: Debian/Ubuntu (apt)
Run as: root
"""

import os
import re
import sys
import time
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlopen, Request

__app__ = "leastBOT"
__version__ = "1.0.1"

# GitHub self-update (optional)
GITHUB_REPO = "mobin-shahhoseini/leastBOT"
BRANCH = "main"
RAW_MAIN_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{BRANCH}/leastbot.py"

SERVICE_DIR = "/etc/systemd/system"
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

# -------------------------
# Utils
# -------------------------
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
        res = subprocess.run(cmd, shell=True, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if check and res.returncode != 0:
            raise subprocess.CalledProcessError(res.returncode, cmd, output=res.stdout)
        return (res.stdout or "")
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
        s = input(c(f"{prompt}{suffix}: ", "bold")).strip()
        if not s and default is not None:
            s = str(default)
        if validator:
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

# -------------------------
# Optional: self update
# -------------------------
def parse_version(v):
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except Exception:
        return (0,0,0)

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
            return

        print(c(f"New version available: {remote_ver} (local={__version__})", "yellow"))
        if not yesno(ask("Update now? (y/n)", default="n")):
            return

        installed_path = Path("/usr/local/bin/leastbot")
        script_path = installed_path if installed_path.exists() else Path(sys.argv[0]).resolve()
        if not script_path.exists():
            print(c("! Script path peyda nashod.", "red"))
            return

        backup = script_path.with_suffix(script_path.suffix + ".bak")
        shutil.copy2(script_path, backup)

        tmp = script_path.with_suffix(".tmp")
        tmp.write_text(txt, encoding="utf-8")
        tmp.chmod(script_path.stat().st_mode)
        tmp.replace(script_path)

        print(c(f"✓ Updated. Backup: {backup}", "green"))
        print(c("Restart script.", "cyan"))
        sys.exit(0)

    except Exception as e:
        print(c(f"! Update error: {e}", "yellow"))

# -------------------------
# Install helpers
# -------------------------
def ensure_cmd(cmd_name, apt_pkg=None):
    if shutil.which(cmd_name):
        return
    if apt_pkg is None:
        apt_pkg = cmd_name
    print(c(f"-> '{cmd_name}' peyda nashod, dar hale nasb: {apt_pkg}", "yellow"))
    run("apt update")
    run(f"apt install -y {apt_pkg}")

def ensure_basics_iran():
    ensure_cmd("ssh", "openssh-client")
    ensure_cmd("ssh-keygen", "openssh-client")
    ensure_cmd("ssh-copy-id", "openssh-client")
    ensure_cmd("autossh", "autossh")
    ensure_cmd("ss", "iproute2")

def ensure_basics_kharj():
    ensure_cmd("ss", "iproute2")
    if not shutil.which("sshd"):
        print(c("! sshd peyda nashod. openssh-server nasb nist.", "yellow"))
        if yesno(ask("Install openssh-server? (y/n)", default="y")):
            run("apt update")
            run("apt install -y openssh-server")

def ensure_key():
    key_path = Path("/root/.ssh/id_ed25519")
    pub_path = Path("/root/.ssh/id_ed25519.pub")
    key_dir = Path("/root/.ssh")
    key_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(str(key_dir), 0o700)

    if key_path.exists() and pub_path.exists():
        return

    print(c("-> SSH key mojood nist, dar hale sakht (ed25519)...", "yellow"))
    run('ssh-keygen -t ed25519 -N "" -f /root/.ssh/id_ed25519')

def ssh_copy_id(user, host, ssh_port):
    print(c("-> Dar hale ersal key be Kharj (password mikhad)...", "yellow"))
    run(f"ssh-copy-id -p {ssh_port} {user}@{host}", check=True)

def test_ssh(user, host, ssh_port):
    out = run(
        f'ssh -p {ssh_port} -o StrictHostKeyChecking=accept-new {user}@{host} "echo OK"',
        capture=True,
        check=False,
    )
    return "OK" in (out or "")

def remote_port_free(user, host, ssh_port, port, bind_host):
    # Check if port is already LISTEN on remote
    cmd = (
        f'ssh -p {ssh_port} -o StrictHostKeyChecking=accept-new {user}@{host} '
        f'"ss -lnt | awk \'{{print $4}}\' | grep -E \'^({bind_host}|\\*|0\\.0\\.0\\.0|\\[::\\]):{port}$\' >/dev/null; '
        f'echo $?"'
    )
    out = run(cmd, capture=True, check=False).strip()
    # out should be 0 if found, else 1 (or error)
    return out != "0"

# -------------------------
# Systemd service
# -------------------------
def service_name(remote_port, local_port, remote_ip):
    safe_ip = remote_ip.replace(".", "-")
    return f"leastbot-r{remote_port}-l{local_port}-{safe_ip}.service"

def write_service_file(remote_user, remote_ip, ssh_port, local_port, remote_port, bind_public):
    """
    Reverse tunnel:
    Iran(local):  127.0.0.1:local_port
    Kharj(remote): bind_host:remote_port  (bind_host=0.0.0.0 if public else 127.0.0.1)
    """
    svc = service_name(remote_port, local_port, remote_ip)
    service_path = f"{SERVICE_DIR}/{svc}"

    bind_host = "0.0.0.0" if bind_public else "127.0.0.1"

    # StartLimitIntervalSec belongs to [Unit], not [Service]
    content = f"""[Unit]
Description=leastBOT Reverse SSH Tunnel IR -> KHAREJ (R:{remote_port} -> L:{local_port})
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=root
Environment="AUTOSSH_GATETIME=0"
ExecStart=/usr/bin/autossh -M 0 -N \\
  -o ServerAliveInterval=30 \\
  -o ServerAliveCountMax=3 \\
  -o ExitOnForwardFailure=yes \\
  -o StrictHostKeyChecking=accept-new \\
  -p {ssh_port} \\
  -R {bind_host}:{remote_port}:127.0.0.1:{local_port} \\
  {remote_user}@{remote_ip}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
    print(c(f"-> Writing service: {service_path}", "yellow"))
    with open(service_path, "w", encoding="utf-8") as f:
        f.write(content)

    return svc, bind_host

def systemd_enable_start(svc):
    run("systemctl daemon-reload")
    run(f"systemctl enable --now {svc}")
    run(f"systemctl status {svc} --no-pager", check=False)

def systemd_stop_remove_by_name(svc):
    run(f"systemctl disable --now {svc}", check=False)
    path = f"{SERVICE_DIR}/{svc}"
    if os.path.exists(path):
        os.remove(path)
        print(c(f"✓ Removed: {path}", "green"))
    run("systemctl daemon-reload")

def list_leastbot_services():
    out = run("systemctl list-units --type=service --all | grep leastbot- || true",
              capture=True, check=False)
    return out.strip()

# -------------------------
# Firewall & sshd on Kharj
# -------------------------
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

def open_port(port):
    fw = detect_firewall()
    print(c(f"-> Firewall: {fw}", "yellow"))
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
        print(c("! iptables rule added (may be lost after reboot).", "yellow"))
    else:
        print(c("! No active firewall tool detected. If port is blocked upstream, open it there too.", "yellow"))

def ensure_sshd_config():
    path = "/etc/ssh/sshd_config"
    if not os.path.exists(path):
        raise RuntimeError("File /etc/ssh/sshd_config peyda nashod.")

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
    set_or_add("ClientAliveInterval", "30")
    set_or_add("ClientAliveCountMax", "3")

    backup = path + ".leastbot.bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
        print(c(f"✓ Backup: {backup}", "green"))

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(c("✓ sshd_config updated (forwarding enabled).", "green"))

def restart_ssh():
    run("systemctl restart ssh", check=False)
    run("systemctl restart sshd", check=False)

def check_listen(port):
    out = run(f"ss -lntp | grep ':{port} ' || true", capture=True, check=False) or ""
    if out.strip():
        print(c(out.strip(), "green"))
    else:
        print(c(f"! No listen for :{port}", "yellow"))

# -------------------------
# Menus
# -------------------------
def print_main_menu():
    print(c("\nMain Menu", "bold"))
    print(c("0) Exit", "dim"))
    print("1) Iran   (Client)  [Create reverse tunnel service]")
    print("2) Kharj  (Server)  [Enable forwarding + open port]")
    print("3) Status / Logs")
    print("4) Remove Tunnel Service (Iran)")
    print("5) Check / Update (GitHub)")
    print("6) List leastBOT services")

def mode_iran():
    print(c("\n=== MODE: IRAN (Client) ===", "bold"))
    print("Create reverse tunnel from Iran to Kharj.\n")

    local_port  = ask("Local port on IRAN (x-ui panel port)", validator=valid_port)
    remote_port = ask("Public port on KHARJ (what you will open)", validator=valid_port)
    remote_ip   = ask("IP server KHARJ", validator=valid_ip)
    remote_user = ask("SSH user on KHARJ", default="root")
    ssh_port    = ask("SSH port on KHARJ", default="22", validator=valid_port)
    pub_choice  = ask("Bind on KHARJ public? (y=0.0.0.0 / n=127.0.0.1)", default="y")
    bind_public = yesno(pub_choice)

    ensure_basics_iran()
    ensure_key()

    print(c("\nTip: On KHARJ run option 2 once to enable GatewayPorts + open firewall.", "yellow"))

    ssh_copy_id(remote_user, remote_ip, ssh_port)

    print(c("\n-> Testing SSH ...", "yellow"))
    if not test_ssh(remote_user, remote_ip, ssh_port):
        print(c("✗ SSH test failed. Fix SSH then retry.", "red"))
        return

    bind_host = "0.0.0.0" if bind_public else "127.0.0.1"
    print(c(f"\n-> Checking remote port {remote_port} availability on {remote_ip} ({bind_host}) ...", "yellow"))
    if not remote_port_free(remote_user, remote_ip, ssh_port, remote_port, bind_host):
        print(c(f"✗ Remote port {remote_port} is already in use on KHARJ. Choose another port.", "red"))
        return

    svc, bind_host = write_service_file(remote_user, remote_ip, ssh_port, int(local_port), int(remote_port), bind_public)
    systemd_enable_start(svc)

    print(c("\n✅ Done!", "green"))
    # IMPORTANT: user requested ONLY IP + PORT, nothing else
    print(c(f"http://{remote_ip}:{remote_port}", "cyan"))
    print(c("Note: If your x-ui has webBasePath not '/', it may show 404 on root. Set webBasePath to '/' inside x-ui.", "yellow"))

def mode_kharj():
    print(c("\n=== MODE: KHARJ (Server) ===", "bold"))
    print("Enable ssh forwarding + open a port in firewall.\n")

    port = ask("Port to open on KHARJ", validator=valid_port)

    ensure_basics_kharj()
    ensure_sshd_config()
    restart_ssh()
    open_port(port)

    print(c("\n--- Check ---", "bold"))
    check_listen(port)

    print(c("\n✅ Done! Test from outside:", "green"))
    print(c(f"http://<IP_KHARJ>:{port}", "cyan"))

def mode_status_logs():
    print(c("\n=== STATUS / LOGS ===", "bold"))
    out = list_leastbot_services()
    if out:
        print(c("\nActive/installed leastBOT services:", "dim"))
        print(out)

    svc = ask("Enter service name (example: leastbot-r2087-l2087-1-2-3-4.service)", validator=None)
    print(c("\n[1] Service status", "bold"))
    run(f"systemctl status {svc} --no-pager", check=False)

    print(c("\n[2] Last logs (journalctl)", "bold"))
    run(f"journalctl -u {svc} -n 200 --no-pager", check=False)

def mode_remove_tunnel():
    print(c("\n=== REMOVE TUNNEL (IRAN) ===", "bold"))
    out = list_leastbot_services()
    if out:
        print(c("\nleastBOT services:", "dim"))
        print(out)
    svc = ask("Enter exact service name to remove", validator=None)
    if not yesno(ask(f"Sure remove {svc}? (y/n)", default="n")):
        print(c("Canceled.", "yellow"))
        return
    systemd_stop_remove_by_name(svc)
    print(c("✅ Removed.", "green"))

def mode_update():
    print(c("\n=== UPDATE (GitHub) ===", "bold"))
    print(c(f"Repo: {GITHUB_REPO}", "cyan"))
    self_update(force=True)

def mode_list():
    print(c("\n=== LIST SERVICES ===", "bold"))
    out = list_leastbot_services()
    if out:
        print(out)
    else:
        print(c("No leastBOT services found.", "yellow"))

def main():
    clear()
    print(LOGO)

    if not is_root():
        print(c("✗ Lotfan ba root ejra kon: sudo -i", "red"))
        return

    spinner("Starting leastBOT", seconds=0.8)

    # Daily silent update check (no prompt unless newer)
    print(c("Checking updates (daily)...", "dim"))
    self_update(force=False)

    while True:
        print_main_menu()
        choice = input(c("\nSelect option [0-6]: ", "bold")).strip()

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
            mode_remove_tunnel()
        elif choice == "5":
            mode_update()
        elif choice == "6":
            mode_list()
        else:
            print(c("✗ Option na-motabar.", "red"))

        input(c("\nEnter bezan ta berim menu ...", "yellow"))
        clear()
        print(LOGO)

if __name__ == "__main__":
    main()
