import pytest
from app import create_app
from app.config import TestingConfig
from app.models import db

@pytest.fixture
def client():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()

def test_status_page_renders(client):
    """Verify /status page returns HTTP 200 and contains required dashboard elements."""
    res = client.get("/status")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "System Status" in html
    assert "Core Temp" in html
    assert "CPU Load" in html
    assert "Memory" in html
    assert "Multi-CNC Machine Hub" in html
    assert "Live Client Stream" in html
    assert "btn-fullscreen" in html
    # Verify standard operations navbar is suppressed in status mode
    assert 'class="nav-bar"' not in html

def test_kiosk_page_renders(client):
    """Verify /kiosk route renders the status dashboard."""
    res = client.get("/kiosk")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "System Status" in html
    assert "btn-fullscreen" in html
    assert 'class="nav-bar"' not in html
