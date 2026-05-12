# This conftest.py file is used to set up the testing environment for the repo_intel tests, 
# ensuring that the root directory of the project is included in the Python path so that the modules can be imported correctly during testing.
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the root directory of the project is in the Python path for test imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
