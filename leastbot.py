#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
leastBOT - Reverse SSH Tunnel Manager
Developer: @leastping
Updates: https://t.me/leastping

Finglish:
leastBOT yek script modiriati baraye sakht Reverse SSH Tunnel (autossh) hast.
Scenario:
- Kharj = Server (public entry)
- Iran  = Client/Entry Point (reverse tunnel az Iran be Kharj)

OS: Debian/Ubuntu (apt)
Run: root
"""

import os
import re
import sys
import time
import shutil
import stat
import subprocess
from pathlib import Path
from urllib.request import urlopen, Request

# =========================
# Version / Repo Config
# =========================
__app__ = "leastBOT"
__version__ = "1.0.0"

# >>>>> IMPORTANT: repo ro inja set kon (USERNAME/REPO)
GITHUB_REPO = "leastping/leastBOT"

RAW_MAIN_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/leastbot.py"
INSTALL_SH_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/install.sh"

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

LOGO = r"""
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   ██╗      ███████╗ █████╗ ███████╗████████╗██████╗  ██████╗ ████████╗       │
│   ██║      ██╔════╝██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗╚══██╔══╝       │
│   ██║      █████╗  ███████║███████╗   ██║   ██████╔╝██║   ██║   ██║          │
│   ██║      ██╔══╝  ██╔══██║╚════██║   ██║   ██╔══██╗██║   ██║   ██║          │
│   ███████╗ ███████╗██║  ██║███████║   ██║   ██████╔╝╚██████╔╝   ██║          │
│   ╚══════╝ ╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═════╝  ╚═════╝    ╚═╝          │
│                                                                              │
│            leastBOT • Reverse SSH Tunnel Manager • v{ver:<8}                  │
│            Iran <-> Kharj  (autossh + systemd)                               │
│                                                                              │
│            Developer: @leastping                                             │
│            Updates only in Telegram: https://t.me/leastping                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
""".format(ver=__version__)

def clear():
    os.system("clear" if os.name != "nt" else "cls")

def spinner(msg="Loading", seconds=1.2):
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    end = time.time() + seconds
    i = 0
    while time.time() < end:
        sys.stdout.write("\r" + c(f"{frames[i%len(frames)]} {msg}...", "cyan"))
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write("\r" + c(f"✓ {msg} done.      ", "green") + "\n")

def run(cmd, check=True, capture=False):
    print(c(f"\n$ {cmd}", "cyan"))
    if capture:
        res = subprocess.run(
            cmd, shell=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        if check and res.returncode != 0:
            raise subprocess.CalledProcessError(res.returncode, cmd, output=res.stdout)
        return res.stdout
    res = subprocess.run(cmd, shell=True)
    if check and res.returncode != 0:
        raise subprocess.CalledProcessError(res.returncode, cmd)
    return None

def is_root():
    return os.geteuid() == 0

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
    except:
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

# =========================
# Auto Update
# =========================
def parse_version(v):
    # "1.2.3" -> (1,2,3)
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except:
        return (0,0,0)

def fetch_url_text(url, timeout=10):
    req = Request(url, headers={"User-Agent": f"{__app__}/{__version__}"})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")

def get_remote_version():
    txt = fetch_url_text(RAW_MAIN_URL, timeout=12)
    m = re.search(r'__version__\s*=\s*"([^"]+)"', txt)
    if not m:
        return None, None
    return m.group(1).strip(), txt

def can_check_updates_daily():
    stamp = CACHE_DIR / "last_update_check.txt"
    now = int(time.time())
    if not stamp.exists():
        return True
    try:
        last = int(stamp.read_text().strip())
        # 24h
        return (now - last) > 86400
    except:
        return True

def mark_checked():
    (CACHE_DIR / "last_update_check.txt").write_text(str(int(time.time())))

def self_update(force=False):
    try:
        if not force and not can_check_updates_daily():
            return

        remote_ver, remote_txt = get_remote_version()
        mark_checked()
        if not remote_ver:
            print(c("! Update check fail shod (remote version peyda nashod).", "yellow"))
            return

        if parse_version(remote_ver) <= parse_version(__version__) and not force:
            print(c(f"✓ Update: no new version. (local={__version__}, remote={remote_ver})", "green"))
            return

        print(c(f"New version available: {remote_ver} (local={__version__})", "yellow"))
        yn = ask("Mikhay update konam? (y/n)", default="y")
        if not yn.lower().startswith("y"):
            print(c("Update cancel shod.", "yellow"))
            return

        script_path = Path(sys.argv[0]).resolve()
        if not script_path.exists():
            print(c("! Nemitoonam script path ro peyda konam.", "red"))
            return

        backup = script_path.with_suffix(script_path.suffix + ".bak")
        shutil.copy2(script_path, backup)

        # write new
        tmp = script_path.with_suffix(".tmp")
        tmp.write_text(remote_txt, encoding="utf-8")

        # preserve exec bit
        mode = script_path.stat().st_mode
        tmp.chmod(mode)

        tmp.replace(script_path)

        print(c(f"✓ Update ok shod. Backup: {backup}", "green"))
        print(c("Restart kon ta version jadid load beshe.", "cyan"))
        sys.exit(0)

    except Exception as e:
        print(c(f"! Update error: {e}", "yellow"))

# =========================
# Install helpers
# =========================
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
    ensure_cmd("curl", "curl")
    ensure_cmd("ss", "iproute2")

def ensure_basics_kharj():
    ensure_cmd("ss", "iproute2")
    ensure_cmd("curl", "curl")
    if not shutil.which("sshd"):
        print(c("! sshd peyda nashod. ehtemalan openssh-server nasb nist.", "yellow"))
        ans = ask("Mikhay openssh-server nasb konam? (y/n)", default="y")
        if ans.lower().startswith("y"):
            run("apt update")
            run("apt install -y openssh-server")

def ensure_key():
    key_path = Path("/root/.ssh/id_ed25519")
    pub_path = Path("/root/.ssh/id_ed25519.pub")
    key_dir = Path("/root/.ssh")
    key_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(str(key_dir), 0o700)

    if key_path.exists() and pub_path.exists():
        print(c("✓ SSH key mojood ast: /root/.ssh/id_ed25519", "green"))
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
    ) or ""
    print(out.strip())
    return "OK" in out

def service_name_for_port(port):
    return f"leastbot-reverse-{port}.service"

def write_service(remote_user, remote_ip, port, local_host="127.0.0.1"):
    svc = service_name_for_port(port)
    service_path = f"{SERVICE_DIR}/{svc}"

    content = f"""[Unit]
Description=leastBOT Reverse SSH Tunnel IR -> KHAREJ ({port})
After=network.target

[Service]
User=root
Environment="AUTOSSH_GATETIME=0"
ExecStart=/usr/bin/autossh -M 0 -N \\
  -o ServerAliveInterval=30 \\
  -o ServerAliveCountMax=3 \\
  -o ExitOnForwardFailure=yes \\
  -R 0.0.0.0:{port}:{local_host}:{port} \\
  {remote_user}@{remote_ip}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    print(c(f"-> Dar hale sakht service: {service_path}", "yellow"))
    with open(service_path, "w", encoding="utf-8") as f:
        f.write(content)

def systemd_enable_start(port):
    svc = service_name_for_port(port)
    run("systemctl daemon-reload")
    run(f"systemctl enable --now {svc}")
    run(f"systemctl status {svc} --no-pager", check=False)

def systemd_stop_remove(port):
    svc = service_name_for_port(port)
    run(f"systemctl disable --now {svc}", check=False)
    path = f"{SERVICE_DIR}/{svc}"
    if os.path.exists(path):
        os.remove(path)
        print(c(f"✓ Service file hazf shod: {path}", "green"))
    run("systemctl daemon-reload")

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
    print(c(f"-> Firewall detect shod: {fw}", "yellow"))
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
        print(c("! iptables rule ezafe shod (momkene ba reboot pak beshe).", "yellow"))
    else:
        print(c("! Firewall tool faal peyda nashod. agar port baste bood dasti baz kon.", "yellow"))

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

    backup = path + ".leastbot.bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
        print(c(f"✓ Backup sakhte shod: {backup}", "green"))

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(c("✓ sshd_config update shod: AllowTcpForwarding/GatewayPorts", "green"))

def restart_ssh():
    run("systemctl restart ssh", check=False)
    run("systemctl restart sshd", check=False)

def check_listen(port):
    out = run(f"ss -lntp | grep ':{port} ' || true", capture=True, check=False) or ""
    if out.strip():
        print(c(out.strip(), "green"))
    else:
        print(c(f"! Hich listen baraye :{port} peyda nashod.", "yellow"))

# =========================
# Menus / Modes
# =========================
def print_main_menu():
    print(c("\nMain Menu", "bold"))
    print(c("0) Exit", "dim"))
    print("1) Iran  (Client / Entry Point)   [Sakht tunnel az Iran be Kharj]")
    print("2) Kharj (Server)                 [Enable forwarding + open port]")
    print("3) Status / Logs")
    print("4) Remove Tunnel Service (Iran)")
    print("5) Check / Update (GitHub)")

def mode_iran():
    print(c("\n=== MODE: IRAN (Client / Entry Point) ===", "bold"))
    print("In mode, reverse tunnel sakhte mishe ke port Iran ro rooye Kharj publish kone.\n")

    port = ask("Port panel (ham Iran ham Kharj yekie)", validator=valid_port)
    remote_ip = ask("IP server Kharj", validator=valid_ip)
    remote_user = ask("SSH user rooye Kharj", default="root")
    ssh_port = ask("SSH port Kharj", default="22", validator=valid_port)

    ensure_basics_iran()
    ensure_key()

    print(c("\nTip: behtar ast rooye Kharj option 2 ro ejra koni ta ssh forwarding ok bashe.", "yellow"))

    ssh_copy_id(remote_user, remote_ip, ssh_port)

    print(c("\n-> Test SSH ...", "yellow"))
    if not test_ssh(remote_user, remote_ip, ssh_port):
        print(c("✗ Test SSH fail shod. aval SSH ro dorost kon, bad dobare run kon.", "red"))
        return

    write_service(remote_user, remote_ip, port)
    systemd_enable_start(port)

    print(c("\n✅ Done!", "green"))
    print(c(f"Final URL: http://{remote_ip}:{port}/", "cyan"))

def mode_kharj():
    print(c("\n=== MODE: KHARJ (Server) ===", "bold"))
    print("In mode, sshd config update mishe + firewall port baz mishe.\n")

    port = ask("Porti ke mikhay rooye Kharj baz va public bashe", validator=valid_port)

    ensure_basics_kharj()
    ensure_sshd_config()
    restart_ssh()
    open_port(port)

    print(c("\n--- Check ---", "bold"))
    print("Listen check (vaghti tunnel up bashe, mamoolan sshd rooye in port listen mishe):")
    check_listen(port)

    print("\nHTTP test (agar service rooye Iran HTTP bashe):")
    run(f"curl -I http://127.0.0.1:{port} || true", check=False)

    print(c("\n✅ Done! az biroon test kon:", "green"))
    print(c(f"http://<IP_Kharj>:{port}/", "cyan"))

def mode_status_logs():
    print(c("\n=== STATUS / LOGS ===", "bold"))
    port = ask("Port ro vared kon (mesal: 2083 ya 80)", validator=valid_port)
    svc = service_name_for_port(port)

    print(c("\n[1] Service status", "bold"))
    run(f"systemctl status {svc} --no-pager", check=False)

    print(c("\n[2] Last logs (journalctl)", "bold"))
    run(f"journalctl -u {svc} -n 120 --no-pager", check=False)

    print(c("\n[3] Listen check (in server)", "bold"))
    check_listen(port)

def mode_remove_tunnel():
    print(c("\n=== REMOVE TUNNEL (IRAN) ===", "bold"))
    port = ask("Porti ke mikhay service-esh hazf beshe", validator=valid_port)
    confirm = ask(f"Motmaeni service port {port} hazf beshe? (y/n)", default="n")
    if not confirm.lower().startswith("y"):
        print(c("Cancel shod.", "yellow"))
        return
    systemd_stop_remove(port)
    print(c("✅ Service remove shod.", "green"))

def mode_update():
    print(c("\n=== UPDATE (GitHub) ===", "bold"))
    print(c(f"Repo: {GITHUB_REPO}", "cyan"))
    self_update(force=True)

# =========================
# Main
# =========================
def main():
    clear()
    print(LOGO)

    if not is_root():
        print(c("✗ Lotfan ba root ejra kon: sudo -i  (ba'd)  python3 leastbot.py", "red"))
        return

    spinner("Starting leastBOT", seconds=1.1)

    # auto update check (1 bar dar 24 saat)
    print(c("Checking updates (daily)...", "dim"))
    self_update(force=False)

    while True:
        print_main_menu()
        choice = input(c("\nSelect option [0-5]: ", "bold")).strip()

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
        else:
            print(c("✗ Option na-motabar.", "red"))

        input(c("\nEnter bezan ta berim menu ...", "yellow"))
        clear()
        print(LOGO)

if __name__ == "__main__":
    main()