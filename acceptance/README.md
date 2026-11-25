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

Verify an extracted, trusted distribution with relative app/server/license/notice/SBOM paths, --artifact pointing to its original compressed artifact, --expected-artifact-sha256 from a trusted independent source, and --output outside the tree. The optional --smoke runs four explicit CLI commands with a disposable user/project directory, a restricted environment and a timeout. It requires an exact --candidate-sha, --expected-artifact-sha256, --expected-inventory and --expected-inventory-sha256. The reviewed inventory is a separately obtained JSON report containing the same candidate, artifact hash/size, expected architecture, complete file hash/size map, contained link map, installed logical bytes and required metadata paths. Obtain both digests from independently authenticated/reviewed build evidence, not the tree under inspection; independently ensure the extracted directory actually came from that artifact. A first static run can produce a report for independent review, but must not certify itself. Never execute untrusted distributions. This does not disable external networking or guarantee child cleanup. Use a disposable runner or VM. --allow-contained-links is opt-in for reviewed packaging layouts. Junctions, directory links, broken, absolute and escaping links remain forbidden. File links must resolve to a regular file inside the distribution.

The inventory measures regular-file logical bytes (not disk allocation), compressed bytes and hashes. It does not establish authenticity, complete secret absence, full native loader compatibility, license/SBOM semantic validity or unrecognized executable formats. No model is downloaded by this utility. Gates A/B/C remain separate and require genuine clean-machine, offline model and independently scored functional evidence. Do not upload private artifacts or raw logs.

## Parallel integration CI contract

Native PR CI checks out the exact PR head, not a synthetic merge commit; main
pushes test the integrated main. This avoids duplicate branch-push/PR jobs.
Each target calls its owner's unittest command only when its sentinel test
file exists. Absent tests or fixture inputs are BLOCKED in the job summary;
a suite with zero tests fails and a suite with skips is PARTIAL, not qualified.
The macOS fixture requires the owner's script and an independently reviewed
fully hash-locked Python 3.12 ARM64 dependency list at
`acceptance/locks/macos-arm64-py312.txt` (not supplied yet). CI creates a disposable isolated build venv, installs only
hash-matching wheels from PyPI while ignoring preinstalled packages, and checks
PyInstaller 6.22.2 in that interpreter before calling
the actual script. No runtime assets, models, secrets, signing credentials,
fixture uploads or releases are involved. Do not populate this path with an
unreviewed lock. Windows/Linux owner tests run without a build dependency lock.

The CI summary identifies the checked-out candidate SHA. Hosted deterministic
tests and fake runtime fixture results are not acceptance gates. Actual build
jobs remain blocked until the owner contracts, verified payloads, locked build
dependencies, final entry point and metadata are integrated.

## Candidate evidence and gate matrix

The report checks separate nonempty license, notice and SBOM files; their legal
and semantic completeness requires independent review. Known thin native
headers and bounded universal Mach-O slice headers are checked; this does not
replace the owners' actual dependency/loader audits.

For each integrated candidate, record exact source SHA, target OS/architecture,
trusted upstream runtime archive digest and manifest, pinned build dependency
lock, final compressed artifact SHA-256 and bytes (after signing if applicable),
installed logical bytes, full inventory digest, and license/SBOM review. Record
artifact build/fixture results separately from these gates:

| Gate | Windows x64 | macOS ARM64 | Linux x64 |
| --- | --- | --- | --- |
| Native deterministic checks | See exact-SHA CI | See exact-SHA CI | See exact-SHA CI |
| Owner packaging unit tests | See job summary | See job summary | See job summary |
| Native fake-runtime fixture | N/A | See job summary | N/A |
| Real model-free build/inspection | BLOCKED | BLOCKED | BLOCKED |
| A: clean-machine install/first launch/retention | BLOCKED | BLOCKED | BLOCKED |
| B: offline real GGUF, randomized genuine tools | BLOCKED | BLOCKED | BLOCKED |
| C: independent real Laravel editing | BLOCKED | BLOCKED | BLOCKED |
| Optional model-selected MCP | NOT RUN | NOT RUN | NOT RUN |

Missing build metadata and artifacts mean bytes/hash NOT MEASURED, not zero.
No signing, publishing or model downloads in baseline PR CI. No fixture
substitutes for real runtime or gates A/B/C. Keep signing/release operations
in separate, explicitly authorized protected environments.

PR #9 adds two parameter-harness baseline oracle assertions. PR #6 changes
only the two disposable Path(d) roots to Path(d).resolve() in that file;
the edits are disjoint and both must survive integration. Do not replace
the negative/reference or genuine tool evidence assertions.
