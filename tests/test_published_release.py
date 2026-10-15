from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "verify_published_release", ROOT / "scripts/verify_published_release.py"
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class PublishedReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.http = self.root / "http"
        for path, content in {
            "distribution/metadata.json": b'{"plugin":{"version":"0.2.5"}}',
            "assets/v-model-overview.svg": b"<svg/>",
            "assets/v-model-overview.png": b"PNG",
        }.items():
            p = self.source / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)
        skill_names = (
            "terraphim-grep",
            "terraphim-agent-learn",
            "terraphim-agent-memory",
            "terraphim-editor",
        )
        dist = self.source / "dist/autoclaw"
        dist.mkdir(parents=True)
        checksums = []
        for name in skill_names:
            filename = f"{name}-0.2.5.zip"
            data = b"actual archive bytes"
            (dist / filename).write_bytes(data)
            checksums.append(f"{hashlib.sha256(data).hexdigest()}  {filename}\n")
        (dist / "SHA256SUMS").write_text("".join(checksums))
        self.assets = {
            p.name: p.read_bytes()
            for d in [self.source / "dist/autoclaw", self.source / "assets"]
            for p in d.iterdir()
        }
        for name, content in self.assets.items():
            p = self.http / "assets" / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)
        directory = str(self.http)

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=directory, **kwargs)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.metadata = {
            "tag_name": "v0.2.5",
            "draft": False,
            "assets": [
                {
                    "name": n,
                    "state": "uploaded",
                    "size": len(v),
                    "browser_download_url": self.base + "/assets/" + n,
                }
                for n, v in self.assets.items()
            ],
        }
        self.save_metadata()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def save_metadata(self):
        p = self.http / "release.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.metadata))

    def verify(self):
        return module.verify_release(
            self.source,
            "v0.2.5",
            api_url=self.base + "/release.json",
            asset_base=self.base + "/assets/",
            timeout=2,
        )

    def test_reads_every_actual_public_asset_and_compares_bytes(self):
        result = self.verify()
        self.assertEqual("PASS", result["status"])
        self.assertEqual(set(self.assets), set(result["assets"]))
        self.assertEqual(
            hashlib.sha256(b"actual archive bytes").hexdigest(),
            result["assets"]["terraphim-grep-0.2.5.zip"]["sha256"],
        )

    def test_changed_download_is_refused(self):
        (self.http / "assets/terraphim-grep-0.2.5.zip").write_bytes(b"changed")
        self.assertRaises(module.ReleaseError, self.verify)

    def test_partial_release_is_refused(self):
        self.metadata["assets"].pop()
        self.save_metadata()
        self.assertRaises(module.ReleaseError, self.verify)

    def test_extra_asset_is_refused(self):
        self.metadata["assets"].append(
            {
                "name": "unexpected.zip",
                "state": "uploaded",
                "size": 1,
                "browser_download_url": self.base + "/assets/unexpected.zip",
            }
        )
        self.save_metadata()
        self.assertRaises(module.ReleaseError, self.verify)

    def test_duplicate_asset_names_are_refused(self):
        self.metadata["assets"].append(self.metadata["assets"][0])
        self.save_metadata()
        self.assertRaises(module.ReleaseError, self.verify)

    def test_wrong_tag_or_draft_is_refused(self):
        self.metadata["draft"] = True
        self.save_metadata()
        self.assertRaises(module.ReleaseError, self.verify)
        self.metadata["draft"] = False
        self.metadata["tag_name"] = "v0.2.4"
        self.save_metadata()
        self.assertRaises(module.ReleaseError, self.verify)

    def test_unexpected_download_url_is_refused(self):
        self.metadata["assets"][0]["browser_download_url"] = self.base + "/different"
        self.save_metadata()
        self.assertRaises(module.ReleaseError, self.verify)

    def test_http_error_is_closed_and_refused(self):
        (self.http / "assets/v-model-overview.svg").unlink()
        self.assertRaises(module.ReleaseError, self.verify)

    def test_source_version_mismatch_is_refused(self):
        (self.source / "distribution/metadata.json").write_text(
            '{"plugin":{"version":"0.2.4"}}'
        )
        self.assertRaises(module.ReleaseError, self.verify)


if __name__ == "__main__":
    unittest.main()
