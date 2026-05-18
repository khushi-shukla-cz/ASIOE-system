import os
from pathlib import Path
from typing import Tuple

UPLOAD_ROOT = os.getenv('BACKEND_UPLOAD_ROOT', str(Path(__file__).parent / 'uploads'))


def ensure_upload_root() -> None:
    os.makedirs(UPLOAD_ROOT, exist_ok=True)


def save_upload(session_id: str, filename: str, content: bytes) -> str:
    """Save uploaded bytes to a path under UPLOAD_ROOT and return the relative path.

    Path format: {UPLOAD_ROOT}/{session_id}/{filename}
    Returns: path string that can be stored in DB (absolute path).
    """
    ensure_upload_root()
    sess_dir = Path(UPLOAD_ROOT) / session_id
    sess_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name
    target = sess_dir / safe_name
    with open(target, 'wb') as f:
        f.write(content)
    return str(target.resolve())
