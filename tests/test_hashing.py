import hashlib

from oilgas.hashing import sha256_file


def test_sha256_file_hashes_file_contents(tmp_path) -> None:
    path = tmp_path / "sample.bin"
    contents = b"oilgas-etl\n" * 100
    path.write_bytes(contents)

    assert sha256_file(path) == hashlib.sha256(contents).hexdigest()


def test_sha256_file_hashes_empty_file(tmp_path) -> None:
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")

    assert path.exists()
    assert sha256_file(path) == hashlib.sha256(b"").hexdigest()
