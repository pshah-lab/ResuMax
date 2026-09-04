import sys
from pathlib import Path
import pytest

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


@pytest.fixture(autouse=True, scope="session")
def preserve_master_profile():
    """Backs up and restores master_profile.json around pytest session."""
    profile_path = root_dir / "master_profile.json"
    backup = profile_path.read_text(encoding="utf-8") if profile_path.exists() else None
    yield
    if backup is not None:
        profile_path.write_text(backup, encoding="utf-8")

