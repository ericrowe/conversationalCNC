import os
import time
import socket
import shutil
import platform
import subprocess
from collections import deque
from datetime import datetime
from threading import Lock
from flask import Blueprint, jsonify, request, current_app
from ..models import MachineProfile, Tool, MaterialPreset, db

system_bp = Blueprint("system", __name__, url_prefix="/api/system")

APP_START_TIME = time.time()
_activity_lock = Lock()
_activity_log = deque(maxlen=25)

def record_activity(operation: str, machine_name: str = "Standard CNC", lines: int = 0, client_ip: str = None, estimated_time_sec: float = 0.0):
    """Thread-safe recording of G-code generation and machine operations."""
    with _activity_lock:
        entry = {
            "id": int(time.time() * 1000),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operation": operation,
            "machine_name": machine_name or "Standard CNC",
            "lines": lines,
            "client_ip": client_ip or "127.0.0.1",
            "estimated_time_sec": round(estimated_time_sec, 1)
        }
        _activity_log.appendleft(entry)

def get_cpu_temp() -> float:
    """Read Raspberry Pi SoC temperature or fallback."""
    # 1. Linux sysfs thermal zone (Raspberry Pi standard)
    thermal_path = "/sys/class/thermal/thermal_zone0/temp"
    if os.path.exists(thermal_path):
        try:
            with open(thermal_path, "r") as f:
                temp_raw = f.read().strip()
                return round(float(temp_raw) / 1000.0, 1)
        except Exception:
            pass

    # 2. vcgencmd fallback if available on Pi OS
    try:
        res = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True, timeout=1)
        if res.returncode == 0 and "temp=" in res.stdout:
            # Output format: temp=48.2'C
            temp_str = res.stdout.strip().replace("temp=", "").replace("'C", "")
            return float(temp_str)
    except Exception:
        pass

    # 3. macOS / standard fallback
    return 42.0

def get_system_load() -> dict:
    """Read CPU load and memory usage with standard Linux / fallback."""
    cpu_percent = 0.0
    # Try /proc/loadavg on Linux
    if os.path.exists("/proc/loadavg"):
        try:
            with open("/proc/loadavg", "r") as f:
                loads = f.read().strip().split()
                cpu_percent = round(float(loads[0]) * 25.0, 1) # Normalized for 4-core Pi
                cpu_percent = min(100.0, max(0.0, cpu_percent))
        except Exception:
            cpu_percent = 5.0
    else:
        cpu_percent = 8.5

    # Memory usage
    ram_total_mb = 4096
    ram_used_mb = 350
    ram_percent = 8.5

    if os.path.exists("/proc/meminfo"):
        try:
            meminfo = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        meminfo[parts[0].strip()] = int(parts[1].split()[0])
            total_kb = meminfo.get("MemTotal", 4096000)
            avail_kb = meminfo.get("MemAvailable", total_kb - 350000)
            used_kb = total_kb - avail_kb
            ram_total_mb = int(total_kb / 1024)
            ram_used_mb = int(used_kb / 1024)
            ram_percent = round((ram_used_mb / ram_total_mb) * 100.0, 1)
        except Exception:
            pass

    # Disk usage
    disk = shutil.disk_usage("/")
    disk_total_gb = round(disk.total / (1024**3), 1)
    disk_free_gb = round(disk.free / (1024**3), 1)
    disk_used_gb = round(disk.used / (1024**3), 1)
    disk_percent = round((disk.used / disk.total) * 100.0, 1)

    return {
        "cpu_percent": cpu_percent,
        "ram_total_mb": ram_total_mb,
        "ram_used_mb": ram_used_mb,
        "ram_percent": ram_percent,
        "disk_total_gb": disk_total_gb,
        "disk_free_gb": disk_free_gb,
        "disk_used_gb": disk_used_gb,
        "disk_percent": disk_percent
    }

def get_network_ips() -> dict:
    """Detect local IP addresses for network interfaces."""
    ips = {"primary": "127.0.0.1", "interfaces": []}
    try:
        # Connect to a dummy external address to find primary routing interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
        ips["primary"] = primary_ip
    except Exception:
        primary_ip = "127.0.0.1"

    # Inspect interfaces via ip command if available
    try:
        res = subprocess.run(["ip", "-br", "a"], capture_output=True, text=True, timeout=1)
        if res.returncode == 0:
            for line in res.stdout.strip().splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[1] == "UP":
                    ifname = parts[0]
                    ip_cidr = parts[2]
                    ip_addr = ip_cidr.split("/")[0]
                    ips["interfaces"].append({"interface": ifname, "ip": ip_addr})
    except Exception:
        ips["interfaces"].append({"interface": "eth0/wlan0", "ip": primary_ip})

    return ips

def check_rack_backup_status() -> dict:
    """Check if server rack Node 04 (pi-backup.local / pi-backup.lan) is reachable and last backup info."""
    rack_host = os.environ.get("RACK_BACKUP_HOST", "pi-backup.local")
    candidate_hosts = [rack_host, "pi-backup.local", "pi-backup.lan"]
    seen = set()
    rack_online = False
    connected_host = rack_host

    for host in candidate_hosts:
        if not host or host in seen:
            continue
        seen.add(host)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.6)
            s.connect((host, 22))
            s.close()
            rack_online = True
            connected_host = host
            break
        except Exception:
            continue

    last_backup_time = "Never"
    backup_file = "/tmp/conversational_cnc_backup.db"
    if os.path.exists(backup_file):
        try:
            mtime = os.path.getmtime(backup_file)
            last_backup_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    return {
        "rack_backup_host": connected_host,
        "rack_online": rack_online,
        "mode": "rack_integrated" if rack_online else "standalone_local",
        "last_backup": last_backup_time
    }

@system_bp.route("/status", methods=["GET"])
def get_system_status():
    """Comprehensive real-time telemetry endpoint for 7" touchscreen and remote monitoring."""
    uptime_sec = int(time.time() - APP_START_TIME)
    load = get_system_load()
    temp_c = get_cpu_temp()
    net = get_network_ips()
    backup_info = check_rack_backup_status()

    # Query database catalog counts safely
    machines_count = 0
    tools_count = 0
    materials_count = 0
    machines_list = []
    db_size_kb = 0

    try:
        machines = MachineProfile.query.all()
        machines_count = len(machines)
        machines_list = [
            {
                "id": m.id,
                "name": m.name,
                "controller_type": m.controller_dialect.upper() if m.controller_dialect else "GRBL",
                "controller_dialect": m.controller_dialect,
                "work_area_x": m.work_area_x,
                "work_area_y": m.work_area_y,
                "work_area_z": m.work_area_z,
                "max_x": m.work_area_x,
                "max_y": m.work_area_y,
                "max_z": m.work_area_z,
                "is_active": m.is_active
            }
            for m in machines
        ]
        tools_count = Tool.query.count()
        materials_count = MaterialPreset.query.count()

        db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if db_uri.startswith("sqlite:///"):
            db_path = db_uri.replace("sqlite:///", "")
            if os.path.exists(db_path):
                db_size_kb = int(os.path.getsize(db_path) / 1024)
    except Exception as e:
        current_app.logger.warning(f"Database query error in status endpoint: {e}")

    with _activity_lock:
        recent_activity = list(_activity_log)

    return jsonify({
        "status": "online",
        "service": "Conversational CNC Controller Server",
        "version": "1.0.0",
        "hostname": platform.node(),
        "platform": platform.platform(),
        "arch": platform.machine(),
        "python_version": platform.python_version(),
        "uptime_seconds": uptime_sec,
        "uptime_human": f"{uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m {uptime_sec % 60}s",
        "hardware": {
            "cpu_temp_c": temp_c,
            "cpu_percent": load["cpu_percent"],
            "ram_total_mb": load["ram_total_mb"],
            "ram_used_mb": load["ram_used_mb"],
            "ram_percent": load["ram_percent"],
            "disk_total_gb": load["disk_total_gb"],
            "disk_used_gb": load["disk_used_gb"],
            "disk_free_gb": load["disk_free_gb"],
            "disk_percent": load["disk_percent"]
        },
        "network": net,
        "catalog": {
            "machines_count": machines_count,
            "tools_count": tools_count,
            "materials_count": materials_count,
            "database_size_kb": db_size_kb,
            "machines": machines_list
        },
        "backup": backup_info,
        "recent_activity": recent_activity
    }), 200

@system_bp.route("/activity", methods=["GET"])
def get_activity():
    """Return live activity log stream."""
    with _activity_lock:
        return jsonify(list(_activity_log)), 200

@system_bp.route("/backup", methods=["POST"])
def trigger_backup():
    """Trigger an atomic SQLite backup snapshot."""
    try:
        db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if db_uri.startswith("sqlite:///"):
            db_path = db_uri.replace("sqlite:///", "")
            target_path = "/tmp/conversational_cnc_backup.db"
            if os.path.exists(target_path):
                os.remove(target_path)
            
            with db.engine.connect() as conn:
                conn.exec_driver_sql(f"VACUUM INTO '{target_path}'")

            backup_size = os.path.getsize(target_path)
            record_activity(
                operation="Manual SQLite Backup",
                machine_name="System Database",
                lines=0,
                client_ip=request.remote_addr,
                estimated_time_sec=0.1
            )
            return jsonify({
                "status": "success",
                "message": "Atomic database snapshot created successfully",
                "target_file": target_path,
                "size_bytes": backup_size
            }), 200
        else:
            return jsonify({"status": "skipped", "message": "In-memory or non-SQLite database active"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@system_bp.route("/restart", methods=["POST"])
def restart_service():
    """Trigger system service restart."""
    record_activity(
        operation="Server Restart Requested",
        machine_name="System Host",
        lines=0,
        client_ip=request.remote_addr
    )
    if current_app.config.get("TESTING"):
        return jsonify({"status": "success", "message": "Test mode: restart command acknowledged"}), 200

    def _do_restart():
        time.sleep(1)
        try:
            subprocess.run(["sudo", "systemctl", "restart", "conversational-cnc.service"], timeout=5)
        except Exception:
            pass

    import threading
    threading.Thread(target=_do_restart, daemon=True).start()
    return jsonify({"status": "success", "message": "Restart command issued to systemd"}), 200

@system_bp.route("/reboot", methods=["POST"])
def reboot_host():
    """Trigger Raspberry Pi hardware reboot."""
    record_activity(
        operation="Host Reboot Requested",
        machine_name="Raspberry Pi",
        lines=0,
        client_ip=request.remote_addr
    )
    if current_app.config.get("TESTING"):
        return jsonify({"status": "success", "message": "Test mode: reboot command acknowledged"}), 200

    def _do_reboot():
        time.sleep(1)
        try:
            res = subprocess.run(["sudo", "reboot"], capture_output=True, timeout=5)
            if res.returncode != 0:
                subprocess.run(["systemctl", "reboot"], timeout=5)
        except Exception:
            try:
                subprocess.run(["reboot"], timeout=5)
            except Exception:
                pass

    import threading
    threading.Thread(target=_do_reboot, daemon=True).start()
    return jsonify({"status": "success", "message": "Reboot command dispatched to host"}), 200

@system_bp.route("/shutdown", methods=["POST"])
def shutdown_host():
    """Trigger Raspberry Pi hardware poweroff/shutdown."""
    record_activity(
        operation="Host Poweroff Requested",
        machine_name="Raspberry Pi",
        lines=0,
        client_ip=request.remote_addr
    )
    if current_app.config.get("TESTING"):
        return jsonify({"status": "success", "message": "Test mode: shutdown command acknowledged"}), 200

    def _do_shutdown():
        time.sleep(1)
        try:
            res = subprocess.run(["sudo", "poweroff"], capture_output=True, timeout=5)
            if res.returncode != 0:
                subprocess.run(["systemctl", "poweroff"], timeout=5)
        except Exception:
            try:
                subprocess.run(["poweroff"], timeout=5)
            except Exception:
                pass

    import threading
    threading.Thread(target=_do_shutdown, daemon=True).start()
    return jsonify({"status": "success", "message": "Shutdown command dispatched to host"}), 200
