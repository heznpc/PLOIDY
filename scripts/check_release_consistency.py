#!/usr/bin/env python3
"""Check that static release mirrors match the package version."""

from __future__ import annotations

import argparse
import re
import tarfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package_version() -> str:
    """Read the authoritative version from ``pyproject.toml``."""
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def require_pattern(relative_path: str, pattern: str, description: str) -> None:
    """Raise when a release mirror does not contain the expected value."""
    text = (ROOT / relative_path).read_text(encoding="utf-8")
    if re.search(pattern, text, flags=re.MULTILINE) is None:
        raise SystemExit(f"{relative_path}: missing {description}")


def check_mirrors(version: str) -> None:
    """Validate every public surface that must carry a static version."""
    escaped = re.escape(version)
    checks = (
        ("CITATION.cff", rf"^version:\s*[\"']?{escaped}[\"']?\s*$", f"version {version}"),
        (
            "deploy/helm/ploidy/Chart.yaml",
            rf"^version:\s*[\"']?{escaped}[\"']?\s*$",
            f"chart version {version}",
        ),
        (
            "deploy/helm/ploidy/Chart.yaml",
            rf"^appVersion:\s*[\"']?{escaped}[\"']?\s*$",
            f"appVersion {version}",
        ),
        (
            "deploy/helm/ploidy/values.yaml",
            rf"^\s*tag:\s*[\"']?{escaped}[\"']?\s*$",
            f"image tag {version}",
        ),
        (
            "deploy/kubernetes/ploidy.yaml",
            rf"image:\s*ghcr\.io/heznpc/ploidy:{escaped}\s*$",
            f"image tag {version}",
        ),
        (
            "deploy/fly/fly.toml",
            rf"image\s*=\s*[\"']ghcr\.io/heznpc/ploidy:{escaped}[\"']",
            f"image tag {version}",
        ),
        (
            "docker-compose.yml",
            rf"image:\s*ghcr\.io/heznpc/ploidy:{escaped}\s*$",
            f"image tag {version}",
        ),
        (
            "Dockerfile",
            rf"^ARG PLOIDY_VERSION={escaped}\s*$",
            f"build argument {version}",
        ),
    )
    for check in checks:
        require_pattern(*check)


def check_distribution_contents(dist_dir: Path, version: str) -> None:
    """Ensure PyPI artifacts contain service surfaces and no research corpus."""
    sdist = dist_dir / f"ploidy-{version}.tar.gz"
    wheel = dist_dir / f"ploidy-{version}-py3-none-any.whl"
    if not sdist.is_file() or not wheel.is_file():
        raise SystemExit(f"expected one sdist and wheel for {version} in {dist_dir}")

    allowed_sdist_roots = {
        ".dockerignore",
        ".gitignore",
        "CITATION.cff",
        "Dockerfile",
        "LICENSE",
        "PKG-INFO",
        "README.md",
        "SECURITY.md",
        "deploy",
        "docker-compose.yml",
        "docs",
        "mkdocs.yml",
        "pyproject.toml",
        "scripts",
        "src",
        "tests",
        "uv.lock",
    }
    with tarfile.open(sdist, "r:gz") as archive:
        unexpected = set()
        for member in archive.getmembers():
            parts = Path(member.name).parts
            if len(parts) > 1 and parts[1] not in allowed_sdist_roots:
                unexpected.add(parts[1])
    if unexpected:
        raise SystemExit(f"sdist contains non-service roots: {sorted(unexpected)}")

    with zipfile.ZipFile(wheel) as archive:
        unexpected = sorted(
            name
            for name in archive.namelist()
            if not (name.startswith("ploidy/") or name.startswith(f"ploidy-{version}.dist-info/"))
        )
    if unexpected:
        raise SystemExit(f"wheel contains unexpected paths: {unexpected}")


def main() -> None:
    """Run package, mirror, and optional Git tag checks."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="Expected release tag, such as v0.4.0")
    parser.add_argument(
        "--dist-dir",
        type=Path,
        help="Also verify the built wheel and sdist at this path",
    )
    args = parser.parse_args()

    version = package_version()
    check_mirrors(version)
    if args.tag is not None:
        tag_version = args.tag.removeprefix("v")
        if tag_version != version:
            raise SystemExit(f"release tag {args.tag!r} does not match package version {version!r}")
    if args.dist_dir is not None:
        check_distribution_contents(args.dist_dir, version)
    print(f"release surfaces agree on {version}")


if __name__ == "__main__":
    main()
