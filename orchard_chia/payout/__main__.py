# SPDX-License-Identifier: Apache-2.0
"""Entry point: `python -m orchard_chia.payout`."""
from .main import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
