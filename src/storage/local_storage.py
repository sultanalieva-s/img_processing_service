import os
import shutil
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO


class LocalStorage:
    """Stores files under a root folder, addressed by relative keys.

    Example: key "images/<uuid>/original.jpg" -> <root>/images/<uuid>/original.jpg
    """

    def __init__(self, root: str | Path):
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        path = (self._root / key).resolve()
        # blocks path traversal such as "../../etc/passwd"
        if not path.is_relative_to(self._root):
            raise ValueError("Invalid storage key.")
        return path

    def path(self, key: str) -> Path:
        return self._resolve(key)

    def save(self, key: str, data: BinaryIO) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write to a temp file in the same folder, then rename. The rename is
        # atomic, so readers never see a half-written file.
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as out:
                shutil.copyfileobj(data, out, length=64 * 1024)  # streams in chunks
            os.replace(tmp_name, path)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise

    def delete(self, key: str) -> None:
        self._resolve(key).unlink(missing_ok=True)

    def delete_prefix(self, prefix: str) -> None:
        """Delete a whole "folder", e.g. everything under images/<uuid>."""
        path = self._resolve(prefix)
        if path == self._root:
            raise ValueError("Refusing to delete the storage root.")
        shutil.rmtree(path, ignore_errors=True)


@lru_cache
def get_storage() -> LocalStorage:
    return LocalStorage("/data/uploads")