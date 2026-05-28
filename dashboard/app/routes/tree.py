# SPDX-License-Identifier: Apache-2.0
"""Live-view page for a single Tree.

The HTML is mostly static — actual data is fetched by JS polling the
`/api/tree/<node_id>/latest` endpoint on a short interval.
"""
from __future__ import annotations

from flask import Blueprint, abort, render_template

from .. import oracle_client

bp = Blueprint("tree", __name__)


@bp.route("/tree/<node_id>")
def tree_page(node_id: str):
    node = oracle_client.get_node(node_id.upper())
    if node is None:
        abort(404)
    return render_template("tree.html", node=node)
