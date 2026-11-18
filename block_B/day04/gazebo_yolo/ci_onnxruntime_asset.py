#!/usr/bin/env python3
"""Public CI-only prefetch of pinned ONNX Runtime release asset through GitHub REST.

Do not patch upstream yolo_ros, do not run on Owner WSL2, and never accept
the 9-byte "Forbidden" or 504 HTML payload as a tarball.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tarfile
import tempfile
from urllib.request import Request, urlopen

ONNXRUNTIME_VERSION = "1.20.0"
ASSET = f"onnxruntime-linux-x64-{ONNXRUNTIME_VERSION}.tgz"
BASE = "https://api.github.com/repos/microsoft/onnxruntime"
RELEASE_URL = f"{BASE}/releases/tags/v{ONNXRUNTIME_VERSION}"
PREFIX = ASSET[:-4] + "/"
REQUIRED = [
    PREFIX + "lib/libonnxruntime.so",
    PREFIX + "include/onnxruntime_c_api.h",
    PREFIX + "LICENSE",
    PREFIX + "ThirdPartyNotices.txt",
]


class ArchiveRejected(ValueError):
    pass


def check_archive(path: Path) -> str:
    if not path.is_file() or path.stat().st_size < 1024 * 1024:
        raise ArchiveRejected("archive unexpectedly small (e.g. 9-byte Forbidden response)")
    try:
        with tarfile.open(path, "r:gz") as archive:
            names = set(archive.getnames())
            # Official archives sometimes store leading "./".
            names = {name.removeprefix("./") for name in names}
            absent = [n for n in REQUIRED if n not in names]
            if absent:
                raise ArchiveRejected("required runtime entries missing: " + ",".join(absent))
    except (tarfile.TarError, OSError) as exc:
        raise ArchiveRejected(f"invalid gzip/tar archive: {exc}") from exc
    return hashlib.sha256(path.read_bytes()).hexdigest()


def headers(accept: str) -> dict[str, str]:
    h = {
        "Accept": accept,
        "User-Agent": "AXIA-D08-public-CI-asset-prefetch",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        h["Authorization"] = "Bearer " + token
    return h


def get_release_asset() -> dict:
    request = Request(RELEASE_URL, headers=headers("application/vnd.github+json"))
    with urlopen(request, timeout=45) as response:
        metadata = json.load(response)
    matches = [a for a in metadata.get("assets", []) if a.get("name") == ASSET]
    if len(matches) != 1:
        raise ArchiveRejected("pinned release asset missing or ambiguous")
    asset = matches[0]
    if not isinstance(asset.get("id"), int) or int(asset.get("size", 0)) < 1024 * 1024:
        raise ArchiveRejected("invalid release asset ID/size")
    return asset


def fetch(destination: Path) -> str:
    if destination.is_file():
        try:
            return check_archive(destination)
        except ArchiveRejected:
            destination.unlink()
    destination.parent.mkdir(parents=True, exist_ok=True)
    meta = get_release_asset()
    asset_id = meta["id"]
    url = f"{BASE}/releases/assets/{asset_id}"
    request = Request(url, headers=headers("application/octet-stream"))
    tmp = destination.with_name(destination.name + ".download")
    try:
        with urlopen(request, timeout=180) as response, tmp.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                if out.tell() > 64 * 1024 * 1024:
                    raise ArchiveRejected("unexpectedly large ONNX Runtime asset")
        size = tmp.stat().st_size
        if size != meta["size"]:
            raise ArchiveRejected(f"release metadata length mismatch: got={size} expected={meta['size']}")
        digest = check_archive(tmp)
        declared = meta.get("digest") or ""
        if declared:
            if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", declared):
                raise ArchiveRejected("unrecognized upstream digest format")
            if digest != declared.split(":", 1)[1].lower():
                raise ArchiveRejected("official GitHub release SHA256 digest mismatch")
        os.replace(tmp, destination)
        return digest
    finally:
        tmp.unlink(missing_ok=True)


def self_test() -> None:
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / ASSET
        path.write_bytes(b"Forbidden")
        try:
            check_archive(path)
        except ArchiveRejected:
            pass
        else:
            raise AssertionError("bad 9-byte file unexpectedly accepted")
        with tarfile.open(path, "w:gz") as archive:
            for name in REQUIRED:
                # Synthetic archive is padded to >1MiB by random bytes:
                # this tests parser logic only; never ship as runtime.
                data = os.urandom(1024 * 1024 + 32) if name.endswith(".so") else b"fixture"
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        assert re.fullmatch(r"[0-9a-f]{64}", check_archive(path))
    print("CI_ORT_OFFLINE_SELF_TEST_PASS NO_NETWORK ROS_NOT_RUN GAZEBO_NOT_RUN")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--check", type=Path)
    p.add_argument("--fetch", type=Path)
    args = p.parse_args()
    try:
        if args.self_test:
            self_test()
        elif args.check is not None:
            sha = check_archive(args.check)
            print(f"CI_ORT_ARCHIVE_OK sha256={sha}")
        elif args.fetch is not None:
            sha = fetch(args.fetch)
            print(f"CI_ORT_FETCH_PASS version={ONNXRUNTIME_VERSION} sha256={sha} bytes={args.fetch.stat().st_size}")
        else:
            p.error("one of --check / --fetch / --self-test is required")
    except (ArchiveRejected, OSError, ValueError) as exc:
        print(f"CI_ORT_ARCHIVE_REJECTED: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
