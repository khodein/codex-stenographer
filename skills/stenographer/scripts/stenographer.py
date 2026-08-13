#!/usr/bin/env python3

import argparse
import fcntl
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


EVENT_TYPES = (
    "user-request",
    "user-addition",
    "user-decision",
    "agent-comment",
    "agent-response",
    "plan",
    "research",
    "decision",
    "action",
    "tool-call",
    "tool-result",
    "code-change",
    "verification",
    "error",
    "blocker",
    "commit",
    "push",
    "external-action",
)

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)authorization:\s*bearer\s+\S+"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]+\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
)


def run_git(*args: str) -> str:
    result = subprocess.run(
        ("git", *args),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Could not resolve the Git context")
    return result.stdout.strip()


def git_context() -> tuple[Path, str, str]:
    repository_root = Path(run_git("rev-parse", "--show-toplevel")).resolve()
    branch = run_git("branch", "--show-current")
    if not branch:
        raise RuntimeError("The current HEAD is not on a named Git branch")
    return repository_root, repository_root.name, branch


def safe_name(value: str) -> str:
    return value.replace("/", "__")


def transcript_path() -> tuple[Path, Path, str, str]:
    repository_root, repository, branch = git_context()
    transcript_root = Path(
        os.environ.get(
            "STENOGRAPHER_ROOT",
            Path.home() / ".config" / "ai-rules" / "stenographer",
        )
    ).expanduser()
    path = transcript_root / safe_name(repository) / f"{safe_name(branch)}.md"
    return path, repository_root, repository, branch


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def validate_text(values: list[str]) -> None:
    joined = "\n".join(values)
    for pattern in SECRET_PATTERNS:
        if pattern.search(joined):
            raise RuntimeError("Entry rejected: detected data that resembles a secret")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as temporary:
        temporary.write(content.rstrip("\n"))
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def with_lock(path: Path):
    lock_path = path.parent / f".{path.name}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = lock_path.open("a+", encoding="utf-8")
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
    return lock_file


def header(repository_root: Path, repository: str, branch: str, task: str) -> str:
    now = timestamp()
    return (
        f"# {branch}\n\n"
        f"- Repository: `{repository}`\n"
        f"- Path: `{repository_root}`\n"
        f"- Branch: `{branch}`\n"
        f"- Created: `{now}`\n"
        f"- Updated: `{now}`\n"
        f"- Status: `in progress`\n\n"
        "## Context\n\n"
        f"{task.strip()}\n\n"
        "## Events"
    )


def update_timestamp(content: str) -> str:
    return re.sub(
        r"(?m)^- Updated: `[^`]+`$",
        f"- Updated: `{timestamp()}`",
        content,
        count=1,
    )


def update_status(content: str, status: str) -> str:
    return re.sub(
        r"(?m)^- Status: `[^`]+`$",
        f"- Status: `{status}`",
        content,
        count=1,
    )


def event_entry(args: argparse.Namespace) -> str:
    parts = [
        f"### {timestamp()} — {args.title.strip()}",
        f"- Type: `{args.type}`",
        f"- Actor: `{args.actor}`",
    ]
    if args.body:
        parts.extend(("", args.body))
    if args.file:
        parts.extend(("", "Files:"))
        parts.extend(f"- `{item}`" for item in args.file)
    if args.symbol:
        parts.extend(("", "Symbols:"))
        parts.extend(f"- `{item}`" for item in args.symbol)
    if args.command:
        parts.extend(("", f"Command: `{args.command}`"))
    if args.result:
        parts.extend(("", f"Result: {args.result.strip()}"))
    return "\n".join(parts)


def command_show() -> int:
    path, _, _, _ = transcript_path()
    print(f"TRANSCRIPT_PATH={path}")
    if not path.exists():
        print("TRANSCRIPT_STATUS=missing")
        return 0
    print("TRANSCRIPT_STATUS=existing")
    print(path.read_text(encoding="utf-8"))
    return 0


def command_init(task: str) -> int:
    path, repository_root, repository, branch = transcript_path()
    validate_text([task])
    lock_file = with_lock(path)
    try:
        if path.exists():
            print(f"Transcript already exists: {path}")
            return 0
        atomic_write(path, header(repository_root, repository, branch, task))
    finally:
        lock_file.close()
    print(f"Created transcript: {path}")
    return 0


def command_append(args: argparse.Namespace) -> int:
    path, _, _, _ = transcript_path()
    values = [
        args.title,
        args.body or "",
        args.command or "",
        args.result or "",
        *(args.file or []),
        *(args.symbol or []),
    ]
    validate_text(values)
    if args.type in {
        "user-request",
        "user-addition",
        "user-decision",
        "agent-comment",
        "agent-response",
    } and args.body is None:
        raise RuntimeError(f"Event {args.type} requires verbatim text in --body")
    if args.type == "code-change" and not args.file:
        raise RuntimeError(
            "Event code-change requires a complete --file path"
        )
    if args.file and not args.symbol:
        raise RuntimeError(
            "Using --file requires --symbol: a fully qualified class/function name "
            "or 'not applicable: <file type>' for files without a code symbol"
        )
    if not path.exists():
        raise RuntimeError("The transcript does not exist. Run init first")
    lock_file = with_lock(path)
    try:
        content = path.read_text(encoding="utf-8").rstrip("\n")
        content = update_timestamp(content)
        atomic_write(path, f"{content}\n\n{event_entry(args)}")
    finally:
        lock_file.close()
    print(f"Added event: {path}")
    return 0


def command_resume() -> int:
    path, _, _, _ = transcript_path()
    if not path.exists():
        raise RuntimeError("The transcript does not exist. Run init first")
    lock_file = with_lock(path)
    try:
        content = path.read_text(encoding="utf-8").rstrip("\n")
        content = update_status(content, "in progress")
        content = update_timestamp(content)
        atomic_write(path, content)
    finally:
        lock_file.close()
    print("Transcript work resumed: in progress")
    return 0


def command_finish(status: str) -> int:
    path, _, _, _ = transcript_path()
    status = status.strip()
    if not status:
        raise RuntimeError("Completion status cannot be empty")
    if not path.exists():
        raise RuntimeError("The transcript does not exist. Run init first")
    lock_file = with_lock(path)
    try:
        content = path.read_text(encoding="utf-8").rstrip("\n")
        content = update_status(content, status)
        content = update_timestamp(content)
        atomic_write(path, content)
    finally:
        lock_file.close()
    print(f"Updated status: {status}")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Transcribe AI-agent work for each Git branch")
    commands = root.add_subparsers(dest="action", required=True)

    commands.add_parser("show", help="Show the current branch transcript")

    init = commands.add_parser("init", help="Create the current branch transcript")
    init.add_argument("--task", required=True, help="Original task description")

    append = commands.add_parser("append", help="Append an event")
    append.add_argument("--type", required=True, choices=EVENT_TYPES)
    append.add_argument("--title", required=True)
    append.add_argument(
        "--actor",
        default=os.environ.get("STENOGRAPHER_ACTOR", "agent"),
        help=(
            "user for user events, the actual model name for AI actions, "
            "and system for system events"
        ),
    )
    append.add_argument("--body")
    append.add_argument("--file", action="append")
    append.add_argument("--symbol", action="append")
    append.add_argument("--command")
    append.add_argument("--result")

    commands.add_parser("resume", help="Resume work on an existing transcript")

    finish = commands.add_parser("finish", help="Mark branch work as complete")
    finish.add_argument("--status", default="complete", help="Final transcript status")
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.action == "show":
            return command_show()
        if args.action == "init":
            return command_init(args.task)
        if args.action == "append":
            return command_append(args)
        if args.action == "resume":
            return command_resume()
        if args.action == "finish":
            return command_finish(args.status)
        raise RuntimeError(f"Unknown command: {args.action}")
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())