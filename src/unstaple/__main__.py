"""Allow `python -m unstaple`."""

import sys

from .cli import main

sys.exit(main())
