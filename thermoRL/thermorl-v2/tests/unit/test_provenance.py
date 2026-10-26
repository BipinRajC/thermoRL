import hashlib
import json

from thermorl2.experiments.provenance import environment, git_state, sha256_file, write_manifest


def test_write_manifest_roundtrip(tmp_path):
    source = tmp_path / "workload.json"
    source.write_bytes(b"fixed input\n")
    digest = sha256_file(source)
    assert digest == hashlib.sha256(b"fixed input\n").hexdigest()
    path = write_manifest(tmp_path / "provenance", system="lassen", fmu_sha256="pinned", workload_sha256=digest, config={"dt_s": 20}, policy=None, seed=None, timings={"total_s": 0.1})
    manifest = json.loads(path.read_text())
    assert manifest["backend"] == "fmu"
    assert manifest["system"] == "lassen" and manifest["workload_sha256"] == digest
    assert manifest["config"] == {"dt_s": 20}
    assert len(manifest["git"]["sha"]) == 40
    assert isinstance(git_state()["dirty"], bool)
    assert set(environment()) >= {"python", "uv", "fmpy", "numpy", "platform"}
