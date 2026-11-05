from pathlib import Path
from dataclasses import asdict
import json
import os
import tempfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from research.authorization_history_v1 import history
from research.scientific_history_v1.receiver import POLICY, checker_identity
from research.scientific_history_v1.test_receiver import real_config
from research.scientific_witness_v1.store import WitnessStore
from research.scientific_witness_v1.client import WitnessClient
from research.scientific_authority_v2.demo import start_server, sign_intent, write_secret

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "research/scientific_receiver_v1/fixtures"


class Fixture:
    def __init__(self):
        self.directory = tempfile.TemporaryDirectory()
        self.out = Path(self.directory.name)
        self.config = real_config()  # Actual pinned Lean; explicitly partial fixture profile.
        self.first, self.second, self.key = (Ed25519PrivateKey.generate() for _ in range(3))
        self.root = history.Root(self.first.public_key().public_bytes_raw(),
            self.second.public_key().public_bytes_raw(), POLICY, checker_identity(self.config),
            b"v2-test-genesis", (FIXTURES / "zero-step.wire").read_bytes())
        self.anchor = history.initial(self.root)
        self.local = self.out / "producer.sqlite"
        history.History.create(self.local, self.root)
        self.witness_path = self.out / "witness.sqlite"
        WitnessStore.create(self.witness_path, self.root, self.config, self.key)
        self.config_path = self.out / "config.json"
        item = asdict(self.config); item["environment"] = dict(self.config.environment)
        self.config_path.write_text(json.dumps(item))
        (self.out / "root.json").write_bytes(self.root.encode())
        write_secret(self.out / "witness.key", self.key.private_bytes_raw())
        self.process = None
        self.restart()

    def restart(self):
        self.stop()
        (self.out / "ready.json").unlink(missing_ok=True)
        self.process, ready = start_server(self.out, self.config_path)
        self.url = "http://127.0.0.1:" + str(ready["port"])
        self.client = WitnessClient(self.url, self.root, self.config,
                                    self.key.public_key().public_bytes_raw())

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try: self.process.wait(timeout=10)
            except Exception: self.process.kill(); self.process.wait()

    def close(self):
        self.stop(); self.directory.cleanup()

    def signed(self, anchor=None, name="one-step", event_id=b"candidate"):
        return sign_intent(self.root, anchor or self.anchor, self.first, self.second,
                           (FIXTURES / (name + ".wire")).read_bytes(), event_id)


def record(name, value):
    destination = os.environ.get("PCS_AUTHORITY_V2_REPORTS")
    if destination:
        import time
        directory = Path(destination); directory.mkdir(parents=True, exist_ok=True)
        (directory / (name + "-" + str(time.time_ns()) + ".json")).write_text(
            json.dumps(value, sort_keys=True, indent=2) + "\n")
