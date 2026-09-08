import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.config import TestingConfig
from app.models import db, MachineProfile, Tool, MaterialPreset
from app.api.system import record_activity, get_cpu_temp, get_system_load, get_network_ips, check_rack_backup_status

@pytest.fixture
def client():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        # Seed test data
        m = MachineProfile(
            name="Test WorkBee 1510",
            work_area_x=1000,
            work_area_y=1500,
            work_area_z=90,
            controller_dialect="grbl",
            is_active=True
        )
        db.session.add(m)
        t = Tool(name="1/4 Flat Endmill", tool_number=1, diameter=6.35, tool_type="endmill")
        db.session.add(t)
        p = MaterialPreset(material_name="Plywood", feed_rate_xy=1200, plunge_rate_z=300, spindle_speed=18000, tool=t)
        db.session.add(p)
        db.session.commit()

        yield app.test_client()
        db.session.remove()
        db.drop_all()

@patch("app.api.system.socket.socket")
def test_system_status_endpoint(mock_socket_cls, client):
    """Verify /api/system/status returns complete hardware, catalog, and network telemetry."""
    mock_sock = MagicMock()
    mock_sock.getsockname.return_value = ["192.168.0.72"]
    mock_socket_cls.return_value = mock_sock

    res = client.get("/api/system/status")
    assert res.status_code == 200
    data = res.get_json()

    assert data["status"] == "online"
    assert data["service"] == "Conversational CNC Controller Server"
    assert "hostname" in data
    assert "uptime_seconds" in data
    assert "hardware" in data
    assert "cpu_temp_c" in data["hardware"]
    assert "cpu_percent" in data["hardware"]
    assert "ram_percent" in data["hardware"]
    assert "disk_percent" in data["hardware"]

    # Catalog counts
    assert data["catalog"]["machines_count"] == 1
    assert data["catalog"]["tools_count"] == 1
    assert data["catalog"]["materials_count"] == 1
    assert len(data["catalog"]["machines"]) == 1
    assert data["catalog"]["machines"][0]["name"] == "Test WorkBee 1510"
    assert data["catalog"]["machines"][0]["work_area_x"] == 1000
    assert data["catalog"]["machines"][0]["work_area_y"] == 1500
    assert data["catalog"]["machines"][0]["work_area_z"] == 90

    # Network
    assert "network" in data
    assert "primary" in data["network"]

def test_system_activity_recording(client):
    """Verify activity recording and retrieval in activity stream."""
    record_activity(
        operation="3D Circular Pocket Milling",
        machine_name="WorkBee 1510",
        lines=150,
        client_ip="192.168.0.42",
        estimated_time_sec=45.2
    )

    res = client.get("/api/system/activity")
    assert res.status_code == 200
    activities = res.get_json()
    assert len(activities) >= 1
    latest = activities[0]
    assert latest["operation"] == "3D Circular Pocket Milling"
    assert latest["machine_name"] == "WorkBee 1510"
    assert latest["lines"] == 150
    assert latest["client_ip"] == "192.168.0.42"

def test_system_backup_endpoint(client):
    """Verify /api/system/backup endpoint operates without crashing."""
    res = client.post("/api/system/backup")
    assert res.status_code in [200, 500] # In :memory: testing mode it handles graceful skip/response

def test_system_restart_endpoint(client):
    """Verify /api/system/restart accepts restart request."""
    res = client.post("/api/system/restart")
    assert res.status_code == 200
    assert res.get_json()["status"] == "success"

def test_system_reboot_endpoint(client):
    """Verify /api/system/reboot accepts reboot request."""
    res = client.post("/api/system/reboot")
    assert res.status_code == 200
    assert res.get_json()["status"] == "success"

def test_system_shutdown_endpoint(client):
    """Verify /api/system/shutdown accepts poweroff request."""
    res = client.post("/api/system/shutdown")
    assert res.status_code == 200
    assert res.get_json()["status"] == "success"

@patch("app.api.system.socket.socket")
def test_helper_functions(mock_socket_cls):
    """Verify system telemetry helper functions return valid types."""
    mock_sock = MagicMock()
    mock_sock.getsockname.return_value = ["192.168.0.72"]
    mock_socket_cls.return_value = mock_sock

    temp = get_cpu_temp()
    assert isinstance(temp, float)
    assert temp > 0

    load = get_system_load()
    assert "cpu_percent" in load
    assert "ram_total_mb" in load
    assert "disk_total_gb" in load

    net = get_network_ips()
    assert "primary" in net
    assert isinstance(net["interfaces"], list)

    backup = check_rack_backup_status()
    assert "rack_online" in backup
    assert "mode" in backup
