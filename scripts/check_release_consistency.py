#!/usr/bin/env python3
"""Check that static release mirrors match the package version."""

from __future__ import annotations

import argparse
import re
import tomllib
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


def main() -> None:
    """Run package, mirror, and optional Git tag checks."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="Expected release tag, such as v0.4.0")
    args = parser.parse_args()

    version = package_version()
    check_mirrors(version)
    if args.tag is not None:
        tag_version = args.tag.removeprefix("v")
        if tag_version != version:
            raise SystemExit(f"release tag {args.tag!r} does not match package version {version!r}")
    print(f"release surfaces agree on {version}")


if __name__ == "__main__":
    main()
