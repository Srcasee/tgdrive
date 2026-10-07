import json
import os
from pathlib import Path


class VideoCachePlugin:
    name = "video"
    version = "1.0.0"
    capabilities = frozenset({"delivery.chunk-cache"})

    def __init__(self):
        self.root = Path(os.getenv("TGDRIVE_VIDEO_CACHE_ROOT", "/data/cache/video"))
        self.chunk_size = int(os.getenv("TGDRIVE_VIDEO_CHUNK_SIZE", str(4 * 1024 * 1024)))

    def _dir(self, resource_id):
        path = self.root / str(resource_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def exists(self, resource_id, index):
        return self.chunk_path(resource_id, index).exists()

    def chunk_path(self, resource_id, index):
        return self._dir(resource_id) / f"{index:06d}.chunk"

    def read(self, resource_id, index):
        path = self.chunk_path(resource_id, index)
        if not path.exists():
            return None
        return path.read_bytes()

    def write(self, resource_id, index, data):
        self.chunk_path(resource_id, index).write_bytes(data)

    def save_meta(self, resource_id, meta):
        (self._dir(resource_id) / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def load_meta(self, resource_id):
        path = self._dir(resource_id) / "meta.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


PLUGIN = VideoCachePlugin()
