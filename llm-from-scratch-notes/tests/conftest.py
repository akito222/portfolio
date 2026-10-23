"""各 day フォルダのモジュールを import できるようにする。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for day in ["day2", "day3", "day5", "day6", "day7", "day8"]:
    sys.path.insert(0, str(ROOT / day))
