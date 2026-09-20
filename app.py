# Copyright (C) 2026 Ashank Kumar Singh. Licensed under the GNU GPLv3.

"""NicheRadar application entry point."""

from nicheradar.api import app
from nicheradar.main import main

__all__ = ["app"]

if __name__ == "__main__":
    main()
