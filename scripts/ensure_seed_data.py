"""Initialize local runtime data from the tracked seed dataset."""

from __future__ import annotations

import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SEED_DIR = PROJECT_ROOT / "data_seed"


def ensure_seed_data(project_root: Path | None = None) -> list[Path]:
    """Copy missing runtime data files from data_seed without overwriting local data."""
    root = Path(project_root) if project_root else PROJECT_ROOT
    data_dir = root / "data"
    seed_dir = root / "data_seed"

    if not seed_dir.exists():
        return []

    copied: list[Path] = []
    for source in seed_dir.rglob("*"):
        if not source.is_file():
            continue
        relative_path = source.relative_to(seed_dir)
        target = data_dir / relative_path
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target)
    return copied


def main() -> None:
    copied = ensure_seed_data()
    if copied:
        print(f"Initialized {len(copied)} data files from data_seed/.")
    else:
        print("Runtime data is already initialized.")


if __name__ == "__main__":
    main()
