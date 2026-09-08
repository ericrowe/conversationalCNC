import sys
import os

backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.config import DevelopmentConfig

app = create_app(DevelopmentConfig)

if __name__ == "__main__":
    # In production on standalone host, default port is 80 (or 5000 in unprivileged local dev)
    default_port = 80 if hasattr(os, "geteuid") and os.geteuid() == 0 else 5000
    port = int(os.environ.get("PORT", default_port))
    print(f"Starting Conversational CNC Controller Server on port {port} (http://0.0.0.0:{port})...")
    app.run(host="0.0.0.0", port=port, debug=True)
