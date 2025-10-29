#!/usr/bin/python3
# File name   : setup.py (Bookworm-ready)
# Author      : Adeept (modernizado por ChatGPT)
# Date        : 2025/10/29

import os
import sys
import shutil
import subprocess

def run(cmd, check=True):
    print(f"\n==> {cmd}")
    rc = subprocess.call(cmd, shell=True)
    if check and rc != 0:
        print(f"[WARN] Comando falló (rc={rc}): {cmd}")
    return rc

def which(p):
    return shutil.which(p) is not None

# Rutas del proyecto/venv
CUR_FILE = os.path.abspath(__file__)
PROJECT_DIR = os.path.abspath(os.path.dirname(CUR_FILE))            # /home/pi/adeept_rasptank
SERVER_DIR  = os.path.join(PROJECT_DIR, "server")
WEBSERVER   = os.path.join(SERVER_DIR, "webServer.py")
VENV_DIR    = "/opt/rasptank-venv"
VENV_PY     = os.path.join(VENV_DIR, "bin", "python3")
VENV_PIP    = os.path.join(VENV_DIR, "bin", "pip")

# Detecta archivo config.txt (Bookworm usa /boot/firmware)
BOOT_CONFIGS = ["/boot/firmware/config.txt", "/boot/config.txt"]
def get_boot_config():
    for p in BOOT_CONFIGS:
        if os.path.exists(p):
            return p
    # por compatibilidad, devuelve el primero aunque no exista
    return BOOT_CONFIGS[0]

def ensure_line(path, line):
    """Asegura que una línea EXACTA exista en el archivo (si no, la añade)."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
    except FileNotFoundError:
        data = ""
    if line.strip() not in [l.strip() for l in data.splitlines()]:
        data = (data.rstrip("\n") + "\n" + line.strip() + "\n").lstrip("\n")
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"[OK] Añadida línea a {path}: {line.strip()}")
    else:
        print(f"[OK] Línea ya presente en {path}: {line.strip()}")

def sed_comment(path, startswith):
    """Comenta cualquier línea que empiece por 'startswith' (si existe)."""
    if not os.path.exists(path):
        return
    out_lines = []
    changed = False
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.strip().startswith(startswith):
                if not line.strip().startswith("#"):
                    out_lines.append("#" + line)
                    changed = True
                else:
                    out_lines.append(line)
            else:
                out_lines.append(line)
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(out_lines)
        print(f"[OK] Comentada(s) línea(s) '{startswith}' en {path}")

def write_unit_file():
    UNIT_PATH = "/etc/systemd/system/rasptank.service"
    unit = f"""[Unit]
Description=RaspTank Web Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Environment=PYTHONUNBUFFERED=1
WorkingDirectory={SERVER_DIR}
ExecStart={VENV_PY} {WEBSERVER}
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
    with open(UNIT_PATH, "w", encoding="utf-8") as f:
        f.write(unit)
    print(f"[OK] Creado servicio systemd: {UNIT_PATH}")
    run("systemctl daemon-reload")
    run("systemctl enable --now rasptank.service")

def main():
    if os.geteuid() != 0:
        print("Este script debe ejecutarse como root (sudo).")
        sys.exit(1)

    # 1) Paquetes APT modernos (sin Qt4 ni create_ap)
    run("apt-get update")
    # Limpiezas de espacio (opcionales)
    run("apt-get purge -y wolfram-engine", check=False)
    run("apt-get purge -y 'libreoffice*'", check=False)
    run("apt-get -y autoremove", check=False)
    run("apt-get -y clean", check=False)

    # Base para Python + HW + OpenCV + GStreamer + GPIO + WS281x
    apt_pkgs = [
        "python3-full", "python3-venv", "python3-dev", "python3-pip",
        "i2c-tools", "python3-smbus", "libatlas-base-dev",
        "gstreamer1.0-tools", "gstreamer1.0-libav",
        "gstreamer1.0-plugins-base", "gstreamer1.0-plugins-good",
        "python3-opencv", "python3-rpi.gpio", "python3-rpi-ws281x"
    ]
    run("apt-get install -y " + " ".join(apt_pkgs))

    # 2) Crear/actualizar venv (evita PEP 668)
    if not os.path.exists(VENV_DIR):
        run(f"python3 -m venv {VENV_DIR}")
    # Upgrade pip en el venv
    run(f"{VENV_PIP} install --upgrade pip wheel setuptools")

    # 3) Instalar dependencias Python EN el venv (no en el sistema)
    # Nota: No instalamos OpenCV por pip; ya lo instalamos por APT.
    py_pkgs = [
        "flask", "flask_cors", "websockets",
        "imutils", "pyzmq", "pybase64", "psutil",
        "luma.oled", "mpu6050-raspberrypi", "Adafruit_PCA9685"
    ]
    run(f"{VENV_PIP} install " + " ".join(py_pkgs))

    # 4) I2C y cámara (stack moderno: SIN start_x=1)
    if which("raspi-config"):
        run("raspi-config nonint do_i2c 0", check=False)

    boot_cfg = get_boot_config()
    # Asegura i2c activado
    ensure_line(boot_cfg, "dtparam=i2c_arm=on")
    # Quita start_x=1 si alguien lo dejó
    sed_comment(boot_cfg, "start_x=1")

    # 5) (Opcional) Copiar /etc/config.txt si existe en el proyecto
    src_cfg = os.path.join(SERVER_DIR, "config.txt")
    if os.path.exists(src_cfg):
        try:
            shutil.copyfile(src_cfg, "/etc/config.txt")
            print("[OK] Copiado config.txt a /etc/config.txt")
        except Exception as e:
            print(f"[WARN] No se pudo copiar /etc/config.txt: {e}")

    # 6) Crear servicio systemd en lugar de rc.local/startup.sh
    # Limpia restos antiguos si existen
    try:
        if os.path.exists("/home/pi/startup.sh"):
            os.remove("/home/pi/startup.sh")
            print("[OK] Eliminado /home/pi/startup.sh legado")
    except Exception as e:
        print(f"[WARN] No se pudo eliminar startup.sh: {e}")

    # Quita inyección de rc.local (si quedó en instalaciones viejas)
    rc_local = "/etc/rc.local"
    if os.path.exists(rc_local):
        try:
            with open(rc_local, "r", encoding="utf-8", errors="ignore") as f:
                data = f.read()
            new_data = data.replace("//home/pi/startup.sh start", "")
            if new_data != data:
                with open(rc_local, "w", encoding="utf-8") as f:
                    f.write(new_data)
                print("[OK] Limpiada llamada a startup.sh en /etc/rc.local")
        except Exception as e:
            print(f"[WARN] No se pudo limpiar /etc/rc.local: {e}")

    write_unit_file()

    print("\n===================================================")
    print(" Instalación completa.")
    print(" - Entorno venv:   ", VENV_DIR)
    print(" - Servicio:        rasptank.service (systemd)")
    print(" - WebServer:      ", WEBSERVER)
    print(" - Boot config:    ", boot_cfg, " (i2c habilitado)")
    print("===================================================\n")

    # No forzamos reboot. Si lo deseas:
    # run("reboot")

if __name__ == "__main__":
    main()
