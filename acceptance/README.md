# Deterministic standalone acceptance

Native CI verifies Python 3.12 on Windows 2022 x64, macOS 15 ARM64 and Ubuntu 24.04 x64. It does not qualify a packaged app.

Packaging handoff (provisional contracts observed in PRs 4 and 5):
- Linux: packaging/linux/build.sh VERIFIED_RUNTIME TRUSTED_SHA256SUMS OUTPUT; Ubuntu 24.04, PyInstaller 6.15.0.
- macOS: packaging/macos/build.sh VERIFIED_RUNTIME TRUSTED_INVENTORY_SHA256 NEW_OUTPUT; ARM64, PyInstaller 6.22.2.
- Windows: packaging/windows/verification/payload.py and smoke.ps1 are available; the actual PyInstaller/NSIS prototype and build command remain local.
The runtime workstream now specifies b6500 and a flat runtime-manifest.json schema; its catalog metadata is not a verified staged payload. Packaging owners must reconcile the manifest, trusted inventory, final file layout, signing order and dependency versions before builds can run.

Do not fetch arbitrary runtime assets, generate a trust manifest from unverified files, or combine unrelated branches in release CI. Integrate after reviewed runtime pin, application entry point, dependency locks, license and SBOM paths exist. Builds not run are BLOCKED, not PASS.

From repo root, use Python 3.12:
    python -m unittest discover -s acceptance -v
    python acceptance/verify.py --help

Verify an extracted, trusted distribution with relative app/server/license/notice/SBOM paths, --artifact pointing to its original compressed artifact, --expected-artifact-sha256 from a trusted independent source, and --output outside the tree. The optional --smoke runs four explicit CLI commands with a disposable user/project directory, a restricted environment and a timeout. It requires a trusted artifact digest; independently ensure the extracted directory actually came from that artifact. Never execute untrusted distributions. This does not disable external networking or guarantee child cleanup. Use a disposable runner or VM. --allow-contained-links is opt-in for reviewed packaging layouts. Junctions, directory links, broken, absolute and escaping links remain forbidden. File links must resolve to a regular file inside the distribution.

The inventory measures regular-file logical bytes (not disk allocation), compressed bytes and hashes. It does not establish authenticity, complete secret absence, universal Mach-O support, license/SBOM semantic validity or all dependency architectures. No model is downloaded by this utility. Gates A/B/C remain separate and require genuine clean-machine, offline model and independently scored functional evidence. Do not upload private artifacts or raw logs.
