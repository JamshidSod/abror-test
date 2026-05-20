import sys
from pathlib import Path

# Make `bot` importable from tests without installing the package.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
