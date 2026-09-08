"""Unit and regression tests for status page offline SVG iconography."""
import os
from pathlib import Path
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_status_page_renders_offline_icons(client):
    """Verify status page contains no external CDN font links and references local SVG assets."""
    response = client.get("/status")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Ensure no external CDN fonts or fontawesome links
    assert "cdnjs.cloudflare.com" not in html
    assert "fontawesome" not in html
    assert "fonts.googleapis.com" not in html

    # Verify status page references local SVG icons for all gauges and controls
    assert "/static/icons/reload.svg" in html
    assert "/static/icons/cpu-chip.svg" in html
    assert "/static/icons/temp.svg" in html
    assert "/static/icons/ram.svg" in html
    assert "/static/icons/storage.svg" in html
    assert "/static/icons/machine-status.svg" in html


def test_icon_static_files_valid_svg():
    """Verify all static SVG icon files exist on disk and have valid SVG structure."""
    static_dir = Path(__file__).resolve().parent.parent / "app" / "static" / "icons"
    assert static_dir.exists(), f"Icons directory {static_dir} should exist"

    expected_icons = [
        "reload.svg",
        "cpu-chip.svg",
        "machine-status.svg",
        "temp.svg",
        "ram.svg",
        "storage.svg",
    ]
    for icon_name in expected_icons:
        icon_path = static_dir / icon_name
        assert icon_path.exists(), f"Icon {icon_name} should exist at {icon_path}"
        content = icon_path.read_text(encoding="utf-8").strip()
        assert content.startswith("<svg"), f"{icon_name} should start with <svg"
        assert "viewBox=" in content, f"{icon_name} should contain viewBox attribute"
        assert content.endswith("</svg>"), f"{icon_name} should end with </svg>"
