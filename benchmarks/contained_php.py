"""Opt-in Docker probe for an operator-approved disposable Linux evaluator guest."""

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from math import isfinite
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory, TemporaryFile
from time import monotonic
from typing import Mapping
from uuid import uuid4


SOCKET = Path("/var/run/docker.sock")
IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")
PATH_SEGMENT = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}")
SECRET_SUFFIXES = (".key", ".pem", ".p12", ".pfx")
BRIDGE = "probe_entry.php"
MAX_FIXTURE_BYTES = 64 * 1024 * 1024
MAX_MESSAGE_BYTES = 32 * 1024
CONTROL_TIMEOUT = 10
PROBE_TIMEOUT = 20
VERSION = 1
TMPFS = "rw,noexec,nosuid,nodev,size=32m,mode=1777"


class BlockedReason(str, Enum):
    UNATTRIBUTED = "probe_blocked_unattributed"
    GUEST = "approved_guest_unavailable"
    QUALIFICATION = "guest_qualification_failed"
    FRAMEWORK = "framework_identity_unverified"
    DAEMON = "docker_unavailable"
    IMAGE = "image_unverified"
    STAGING = "fixture_staging_failed"
    POLICY = "container_policy_unverified"
    TRANSPORT = "docker_transport_failed"
    STATE = "execution_state_unverified"
    TIMEOUT = "probe_timeout"
    CLEANUP = "cleanup_unverified"


class EvaluationBlocked(RuntimeError):
    """A named containment requirement could not be verified."""

    def __init__(self, message: str, *, reason: BlockedReason = BlockedReason.UNATTRIBUTED):
        if not isinstance(reason, BlockedReason):
            raise TypeError("Expected a registered blocked reason")
        super().__init__(message)
        self.reason = reason.value


class ContainerCommandDeadline(EvaluationBlocked):
    """A Docker CLI operation exceeded its deadline."""

    def __init__(self, message: str):
        super().__init__(message, reason=BlockedReason.TRANSPORT)


class ProbeDeadlineExceeded(EvaluationBlocked):
    """The attach deadline expired and the probe container was removed."""

    def __init__(self, message: str):
        super().__init__(message, reason=BlockedReason.TIMEOUT)


class CandidateFailure(RuntimeError):
    """A terminated container or successful transport proved a probe failure."""

    def __init__(self, reason: str):
        if reason not in ("candidate_exit", "candidate_resource", "candidate_output"):
            raise ValueError("Unknown probe failure category")
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Observation:
    # These are observations from untrusted PHP, never a qualification verdict.
    response: object
    fixture_sha256: str
    image_id: str
    protocol: int = VERSION


def _stage(root: Path, fixtures: Mapping[str, bytes]) -> str:
    if not 0 < len(fixtures) <= 20_000:
        raise ValueError("Fixture count outside evaluator limits")
    manifest = {}
    total = 0
    for name, content in sorted(fixtures.items()):
        path = PurePosixPath(name)
        if (path.as_posix() != name or not path.parts or len(path.parts) > 32
                or any(not PATH_SEGMENT.fullmatch(part) for part in path.parts)
                or any(part.casefold() in {"tests", "secrets", "credentials", "auth.json", "env"}
                       or part.casefold().endswith(SECRET_SUFFIXES) for part in path.parts)):
            raise ValueError("Fixture path is outside the staged source policy")
        if not isinstance(content, bytes):
            raise ValueError("Fixture content must be explicit bytes")
        total += len(content)
        if total > MAX_FIXTURE_BYTES:
            raise ValueError("Fixture exceeds byte budget")
        target = root.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(content)
        # The guest's unprivileged UID only needs read access.
        target.chmod(0o644)
        for directory in target.parents:
            directory.chmod(0o755)
            if directory == root:
                break
        manifest[name] = hashlib.sha256(content).hexdigest()
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()


def _call(argv: list[str], cwd: Path, deadline_seconds: int, *, data: bytes = b"",
          cap: int = MAX_MESSAGE_BYTES) -> tuple[int, bytes]:
    # Selectors on process pipes are used only on the approved Linux guest.
    deadline = monotonic() + deadline_seconds
    try:
        with TemporaryFile(dir=cwd) as stdin:
            stdin.write(data)
            stdin.seek(0)
            with subprocess.Popen(
                argv, cwd=cwd, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                env={"HOME": str(cwd), "PATH": "/usr/bin:/bin", "LANG": "C"},
            ) as process:
                try:
                    result = bytearray()
                    with selectors.DefaultSelector() as selector:
                        selector.register(process.stdout, selectors.EVENT_READ)
                        while selector.select(max(0, deadline - monotonic())):
                            if monotonic() >= deadline:
                                raise ContainerCommandDeadline("container command deadline exceeded")
                            part = os.read(process.stdout.fileno(), 8192)
                            if not part:
                                return process.wait(timeout=max(0, deadline - monotonic())), bytes(result)
                            result.extend(part)
                            if len(result) > cap:
                                raise EvaluationBlocked("container response exceeds output budget", reason=BlockedReason.TRANSPORT)
                    raise ContainerCommandDeadline("container command deadline exceeded")
                finally:
                    if process.poll() is None:
                        process.kill()
    except subprocess.TimeoutExpired:
        raise ContainerCommandDeadline("container command deadline exceeded") from None
    except OSError:
        raise EvaluationBlocked("container command unavailable", reason=BlockedReason.TRANSPORT) from None


def _create(name: str, fixture: Path, image_id: str) -> list[str]:
    # Docker CSV parsing must not reinterpret the controlled host staging path.
    if any(character in str(fixture) for character in (",", "\n", "\r", '"')):
        raise EvaluationBlocked("unsafe staging path for Docker bind mount", reason=BlockedReason.STAGING)
    return [
        "container", "create", "--name", name, "--pull=never", "--interactive",
        "--network=none", "--ipc=private", "--cgroupns=private", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--read-only", "--user=65534:65534",
        "--pids-limit=32", "--cpus=1", "--memory=512m", "--memory-swap=512m",
        "--ulimit=nofile=128:128", "--no-healthcheck", "--log-driver=none",
        "--mount", f"type=bind,src={fixture},dst=/fixture,readonly,bind-propagation=rprivate",
        "--tmpfs", f"/tmp:{TMPFS}",
        "--workdir=/fixture", "--entrypoint=/usr/bin/env", image_id,
        "-i", "HOME=/tmp", "PATH=/usr/local/bin:/usr/bin:/bin",
        "/usr/local/bin/php", "/tinybuilder/probe.php",
    ]


def _check_container(run, name: str, fixture: Path, image_id: str) -> None:
    status, raw = run(["container", "inspect", "--format", "{{json .}}", name])
    if status != 0:
        raise EvaluationBlocked("created container policy could not be inspected", reason=BlockedReason.POLICY)
    container = _json(raw, reason=BlockedReason.POLICY)
    host = container.get("HostConfig") if isinstance(container, dict) else None
    config = container.get("Config") if isinstance(container, dict) else None
    mounts = container.get("Mounts") if isinstance(container, dict) else None
    required = {
        "NetworkMode": "none", "ReadonlyRootfs": True, "Privileged": False,
        "IpcMode": "private", "CgroupnsMode": "private", "PidsLimit": 32,
        "NanoCpus": 1_000_000_000, "Memory": 512 * 1024 * 1024, "MemorySwap": 512 * 1024 * 1024,
    }
    bind = {"Type": "bind", "Source": str(fixture), "Destination": "/fixture", "RW": False}
    accepted_mounts = False
    if isinstance(mounts, list) and all(isinstance(mount, dict) for mount in mounts):
        # Engine versions may include or omit the tmpfs from the mount summary.
        staged = [mount for mount in mounts if all(mount.get(k) == v for k, v in bind.items())]
        scratch = [mount for mount in mounts
                   if mount.get("Type") == "tmpfs" and mount.get("Destination") == "/tmp"]
        accepted_mounts = len(staged) == 1 and len(scratch) <= 1 and len(mounts) == 1 + len(scratch)
    if (not isinstance(host, dict) or not isinstance(config, dict)
            or container.get("Image") != image_id
            or container.get("Path") != "/usr/bin/env"
            or container.get("Args") != ["-i", "HOME=/tmp", "PATH=/usr/local/bin:/usr/bin:/bin",
                                         "/usr/local/bin/php", "/tinybuilder/probe.php"]
            or any(host.get(key) != value for key, value in required.items())
            or host.get("CapDrop") not in (["ALL"], ["all"]) or host.get("CapAdd")
            or host.get("PidMode") not in ("", "private") or host.get("Devices")
            or host.get("DeviceRequests") or host.get("PortBindings")
            or host.get("SecurityOpt") not in (["no-new-privileges"], ["no-new-privileges=true"])
            or host.get("Tmpfs") != {"/tmp": TMPFS}
            or config.get("User") != "65534:65534"
            or not accepted_mounts):
        raise EvaluationBlocked("created container does not enforce evaluator policy", reason=BlockedReason.POLICY)


def _json(raw: bytes, *, reason: BlockedReason = BlockedReason.UNATTRIBUTED) -> object:
    def unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
        fields = dict(pairs)
        if len(fields) != len(pairs):
            raise ValueError("duplicate JSON fields")
        return fields

    def reject_constant(_value: str) -> None:
        raise ValueError("Invalid JSON constant")

    def finite_float(value: str) -> float:
        result = float(value)
        if not isfinite(result):
            raise ValueError("Non-finite JSON number")
        return result

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_fields,
                          parse_constant=reject_constant, parse_float=finite_float)
    except (ValueError, UnicodeError, RecursionError):
        raise EvaluationBlocked("invalid container observation", reason=reason) from None


def _approved_runtime(docker: Path, image_id: str, approved_guest: bool) -> None:
    if approved_guest is not True or sys.platform != "linux":
        raise EvaluationBlocked("an approved disposable Linux guest is required", reason=BlockedReason.GUEST)
    if not docker.is_absolute() or not docker.is_file():
        raise EvaluationBlocked("an explicitly selected local Docker binary is required", reason=BlockedReason.DAEMON)
    try:
        socket_ok = stat.S_ISSOCK(SOCKET.stat().st_mode)
    except OSError:
        socket_ok = False
    if not socket_ok:
        raise EvaluationBlocked("local Docker socket is unavailable", reason=BlockedReason.DAEMON)
    if not IMAGE_ID.fullmatch(image_id):
        raise EvaluationBlocked("exact local probe image ID is required", reason=BlockedReason.IMAGE)


def _check_engine(run, image_id: str) -> None:
    status, raw = run(["info", "--format", "{{json .}}"])
    if status != 0:
        raise EvaluationBlocked("local Docker engine is unavailable", reason=BlockedReason.DAEMON)
    info = _json(raw, reason=BlockedReason.DAEMON)
    if (not isinstance(info, dict) or info.get("OSType") != "linux"
            or info.get("CgroupVersion") != "2"
            or info.get("CgroupDriver") not in ("cgroupfs", "systemd")
            or any(info.get(limit) is not True for limit in (
                "MemoryLimit", "SwapLimit", "CpuCfsQuota", "PidsLimit"))
            or not isinstance(info.get("SecurityOptions"), list)
            or not any(option in ("name=seccomp,profile=builtin", "name=seccomp,profile=default")
                       for option in info["SecurityOptions"])):
        raise EvaluationBlocked("local container resource or seccomp controls unavailable", reason=BlockedReason.POLICY)
    status, raw = run(["image", "inspect", "--format",
                       '{"id":{{json .Id}},"volumes":{{json .Config.Volumes}}}', image_id])
    if status != 0:
        raise EvaluationBlocked("pinned probe image is unavailable locally", reason=BlockedReason.IMAGE)
    image = _json(raw, reason=BlockedReason.IMAGE)
    if not isinstance(image, dict) or image.get("id") != image_id or image.get("volumes") not in ({}, None):
        raise EvaluationBlocked("probe image identity or declared volumes violate policy", reason=BlockedReason.IMAGE)


def _cleanup(run, name: str) -> None:
    try:
        run(["container", "rm", "--force", "--volumes", name])
    except EvaluationBlocked:
        # Removal may have reached the daemon before the CLI lost its reply.
        pass
    try:
        status, output = run(["container", "ls", "--all", "--quiet", "--filter", f"name={name}"])
    except EvaluationBlocked:
        raise EvaluationBlocked("container cleanup could not be verified", reason=BlockedReason.CLEANUP) from None
    if status != 0 or output.strip():
        raise EvaluationBlocked("container cleanup could not be verified", reason=BlockedReason.CLEANUP)


def _execution_state(run, name: str) -> dict:
    status, raw = run(["container", "inspect", "--format", "{{json .State}}", name])
    if status != 0:
        raise EvaluationBlocked("probe execution state could not be verified", reason=BlockedReason.STATE)
    state = _json(raw, reason=BlockedReason.STATE)
    if not isinstance(state, dict) or state.get("Error") != "":
        raise EvaluationBlocked("probe execution state could not be verified", reason=BlockedReason.STATE)
    return state


def _verify_exit(run, name: str, attach_status: int) -> None:
    state = _execution_state(run, name)
    if (state.get("Status") != "exited" or state.get("Running") is not False
            or type(state.get("ExitCode")) is not int or type(state.get("OOMKilled")) is not bool):
        raise EvaluationBlocked("probe termination was not independently verified", reason=BlockedReason.STATE)
    if state["OOMKilled"] and state["ExitCode"] != 0:
        raise CandidateFailure("candidate_resource")
    if state["OOMKilled"] or state["ExitCode"] != attach_status:
        raise EvaluationBlocked("probe attachment and recorded exit differ", reason=BlockedReason.STATE)
    if state["ExitCode"] != 0:
        raise CandidateFailure("candidate_exit")


def observe(*, docker: Path, image_id: str, fixtures: Mapping[str, bytes], request: object,
            trusted_bridge: bytes, approved_guest: bool = False) -> Observation:
    """Run the pinned PHP probe. Only the outside caller may score its observations."""
    _approved_runtime(docker, image_id, approved_guest)
    if any(name.casefold() == BRIDGE for name in fixtures):
        raise ValueError("Candidate fixture cannot supply the trusted probe bridge")
    payload = json.dumps(request, allow_nan=False).encode()
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ValueError("Probe request exceeds input budget")
    with TemporaryDirectory(prefix="tinybuilder-php-") as temp:
        root = Path(temp)
        fixture = root / "fixture"
        fixture.mkdir()
        try:
            fixture_sha256 = _stage(fixture, {**fixtures, BRIDGE: trusted_bridge})
        except OSError:
            raise EvaluationBlocked("fixture could not be staged", reason=BlockedReason.STAGING) from None
        prefix = [str(docker), "--host", f"unix://{SOCKET}", "--config", temp]

        def run(args: list[str], timeout: int = CONTROL_TIMEOUT, data: bytes = b""):
            return _call([*prefix, *args], root, timeout, data=data)

        _check_engine(run, image_id)
        name = f"tinybuilder-php-{uuid4().hex}"
        create = _create(name, fixture, image_id)
        try:
            status, _ = run(create)
            if status != 0:
                raise EvaluationBlocked("container creation rejected", reason=BlockedReason.POLICY)
            _check_container(run, name, fixture, image_id)
            try:
                status, raw = run(["container", "start", "--attach", "--interactive", name],
                                  PROBE_TIMEOUT, payload)
            except ContainerCommandDeadline:
                state = _execution_state(run, name)
                if state.get("Status") != "running" or state.get("Running") is not True:
                    raise EvaluationBlocked("deadline expired without proof of a running probe", reason=BlockedReason.STATE) from None
                raise ProbeDeadlineExceeded("probe attachment deadline exceeded") from None
            _verify_exit(run, name, status)
        finally:
            _cleanup(run, name)
        try:
            response = _json(raw)
        except EvaluationBlocked:
            raise CandidateFailure("candidate_output") from None
        return Observation(response=response, fixture_sha256=fixture_sha256, image_id=image_id)
