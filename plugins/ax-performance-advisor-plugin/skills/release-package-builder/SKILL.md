---
name: release-package-builder
description: Build a plugin release ZIP with SHA-256 manifest while excluding evidence, output, and cache files.
---

# Release Package Builder

Run `scripts/build_release_package.py` with `--root` and `--output`. Verify the generated manifest and do not include customer evidence or generated output in release packages.
