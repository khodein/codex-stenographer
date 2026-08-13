# Codex Stenographer

`stenographer` is a Codex skill that maintains a chronological task transcript for each Git branch. It records user messages, visible AI responses, actions, tool calls, results, decisions, code changes, and verification events while excluding secrets and hidden model reasoning.

## Why use it?

AI-assisted development can span long sessions, multiple agents, and repeated context resets. Important details often end up scattered across chat history, terminal output, and uncommitted changes. Stenographer turns that activity into a durable, branch-specific record.

This helps you:

- preserve task context between sessions and agents;
- understand why a technical decision was made;
- review which tools, commands, and checks were performed;
- trace code changes back to the request that caused them;
- hand work over without reconstructing the entire conversation;
- keep a useful engineering journal outside the project repository.

Unlike a summary written at the end, the transcript is updated throughout the task. Events stay chronological and separate, making the record useful for investigation, review, and resuming unfinished work.

## What it records

- user requests, clarifications, and decisions;
- visible AI comments and final responses;
- actions, commands, tool calls, and their results;
- plans, implementation decisions, and discovered constraints;
- changed files and affected symbols;
- verification results, errors, commits, pushes, and external actions.

The skill explicitly instructs the agent not to record secrets, raw confidential data, or hidden reasoning.

The skill stores transcripts outside the working repository at:

```text
~/.config/ai-rules/stenographer/<repository>/<branch>.md
```

## Installation

Clone the repository and copy the skill into the Codex skills directory:

```bash
git clone https://github.com/khodein/codex-stenographer.git
mkdir -p ~/.codex/skills
cp -R codex-stenographer/skills/stenographer ~/.codex/skills/
```

Restart Codex or start a new task after installation.

## Usage

Invoke the skill explicitly with `$stenographer`, or add a project instruction requiring it before work in Git repositories.

The included CLI supports:

```bash
python3 ~/.codex/skills/stenographer/scripts/stenographer.py show
python3 ~/.codex/skills/stenographer/scripts/stenographer.py init --task "Task description"
python3 ~/.codex/skills/stenographer/scripts/stenographer.py append --type action --title "Action" --body "Details"
python3 ~/.codex/skills/stenographer/scripts/stenographer.py resume
python3 ~/.codex/skills/stenographer/scripts/stenographer.py finish
```

Run commands from the Git repository whose branch should be transcribed.

## Requirements

- Python 3.9 or newer
- Git
- macOS or another Unix-like system with `fcntl`

## License

MIT
