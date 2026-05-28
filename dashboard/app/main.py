# SPDX-License-Identifier: Apache-2.0
"""Orchard View — Flask application factory.

Run with:
    python -m dashboard.app
or
    flask --app dashboard.app.main:create_app run --host 127.0.0.1 --port 5000
"""
from __future__ import annotations

from flask import Flask

from .config import settings
from .routes import api, dashboard, provision, tree


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(provision.bp)
    app.register_blueprint(tree.bp)
    app.register_blueprint(api.bp, url_prefix="/api")
    return app


# Module-level instance so `flask --app dashboard.app.main` works.
app = create_app()


def main() -> None:
    s = settings()
    app.run(host=s.host, port=s.port, debug=False)


if __name__ == "__main__":
    main()
