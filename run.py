"""Application runner script for PulseCare Hospital Management System."""

import os
from app import create_app

env_name = os.environ.get("FLASK_ENV", "development")
app = create_app(env_name)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
