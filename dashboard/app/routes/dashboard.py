# SPDX-License-Identifier: Apache-2.0
"""Home + nodes-list pages."""
from __future__ import annotations

from flask import Blueprint, render_template

from .. import oracle_client

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    oracle_ok = False
    oracle_info: dict = {}
    nodes: list[dict] = []
    error: str | None = None
    try:
        oracle_info = oracle_client.root()
        oracle_ok = True
        nodes = oracle_client.list_nodes()
    except oracle_client.OracleError as e:
        error = str(e)
    return render_template(
        "index.html",
        oracle_ok=oracle_ok,
        oracle_info=oracle_info,
        nodes=nodes,
        error=error,
    )
