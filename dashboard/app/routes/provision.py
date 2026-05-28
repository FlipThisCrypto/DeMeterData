# SPDX-License-Identifier: Apache-2.0
"""Tree provisioning wizard.

The page renders a form; the actual work happens in `api.py` so the
flow can stay AJAX and the user sees per-step status without a page
reload.
"""
from __future__ import annotations

from flask import Blueprint, render_template

from ..config import settings

bp = Blueprint("provision", __name__)


@bp.route("/provision")
def provision_page():
    return render_template(
        "provision.html",
        default_tree_oracle_url=settings().tree_oracle_url,
    )
