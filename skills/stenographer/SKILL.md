---
name: stenographer
description: "Maintains a complete real-time transcript for work on the current Git branch, recording user messages, visible AI responses, actions, tool calls, results, decisions, changes, and external operations. Use at the start of and continuously throughout every task performed inside a Git repository."
---

# Task Stenographer

## Purpose

Maintain a complete chronological transcript of work performed on the current Git branch. Treat the transcript as a real-time event log, not an end-of-task summary.

Use `~/.codex/skills/stenographer/scripts/stenographer.py`. Run it from the working repository, not from the skill directory: the script resolves the branch with `git rev-parse` and `git branch`, so running it elsewhere produces the wrong Git context.

```bash
python3 ~/.codex/skills/stenographer/scripts/stenographer.py <command>
```

Do not rely on shell aliases because tool calls may run in isolated or non-interactive shells.

Store transcripts outside the repository:

```text
~/.config/ai-rules/stenographer/<repository>/<branch>.md
```

Preserve the branch name in the filename. Replace `/` with `__` to avoid nested directories. Override the storage root with `STENOGRAPHER_ROOT` only when necessary.

## Required task startup

Complete these steps before research, planning, code changes, or external actions:

1. Read this file completely.
2. Run `python3 ~/.codex/skills/stenographer/scripts/stenographer.py show` from the working repository.
3. If a transcript exists, read it completely and run `python3 ~/.codex/skills/stenographer/scripts/stenographer.py resume`.
4. If no transcript exists, run `python3 ~/.codex/skills/stenographer/scripts/stenographer.py init --task "<original user request>"`.
5. Record the current user message as `user-request` for a new transcript or `user-addition` for an existing transcript, with `--actor user`.
6. Only then continue with the task.

Reading this `SKILL.md`, the initial `show`, and any required `init` are bootstrap operations. Do not reconstruct them afterward because reliable recording was not available before the transcript was resolved or created.

For a new transcript, intentionally preserve the original request twice: once in the Context section created by `init`, and once as a chronological `user-request` event.

If the Git branch cannot be resolved, stop transcription, inform the user, and do not invent a transcript path.

## Events to record

Record each event separately and immediately:

- every task-related user message, clarification, decision, approval, and rejection;
- every visible AI comment and final response;
- every AI action, including research, file reads that affect decisions, edits, and external operations;
- every relevant tool call or command, including its purpose and safe parameters;
- every tool or command result, including success, failure, or no result;
- every plan and material plan change;
- every research finding, decision, assumption, error, blocker, and recovery step;
- every created, changed, renamed, or deleted file;
- every affected class, object, interface, top-level function, method, or resource;
- every verification, commit, push, pull request, and external-system update.

Record an event before the next action. Do not replace chronological events with a summary or reconstruct them from memory.

Do not create events for polling that returns no new information or for transcript-writing operations themselves.

Record `tool-call` and `tool-result` for operations that affect the task, such as builds, searches, edits, and external-system calls. Do not create separate events for routine file reads. When a read affects a decision, record its finding directly as `research` or `decision`.

## Events not to record

Do not create events for process-only operations that add no useful task history:

- reading this skill, the initial `show`, `init`, and other bootstrap operations;
- reading project rules, conventions, `AGENTS.md`, or supporting skill instructions;
- routine source-file reads that do not affect a decision;
- announcements of an intended action when the action itself will produce a `commit`, `push`, `code-change`, or `external-action` event.

If a rule or convention affects a decision, capture the effect in a single `decision` or `research` event instead of logging the rule read itself.

## Recording plans

- Record visible draft plans and plan changes as separate `plan` events.
- Before publishing a completed plan to the user, record its full exact content as a `plan` event.
- A file path, link, summary, or chunk list does not replace the full plan.
- When revising an already recorded plan, record only a readable delta with additions (`+`), removals (`-`), changes (`~`), and the reason. Re-record the full plan only after a structural rewrite.

## Content rules

- Preserve every user message and visible AI response verbatim and in full, regardless of length or language.
- Put verbatim messages in `--body`; use `--title` only as a short event label.
- Use `user` for user events, `system` for system events, and the actual model name for AI events. Never leave the generic actor `agent` for AI events.
- Include the full safe command or operation for tool calls and the complete safe result for tool results.
- Redact secrets and confidential data with `[REDACTED]` before calling `append`. The script rejects detected secrets instead of modifying them.
- For very long output, preserve the relevant beginning or decision-making excerpt and replace omitted material with `[truncated N lines]`.
- Never record hidden model reasoning, secrets, tokens, passwords, cookies, personal data, or raw confidential responses.
- For each changed file, use the full repository-relative path.
- For Kotlin or Java, include the fully qualified class, object, interface, method, or top-level function name.
- For XML, Gradle, resources, and files without a code symbol, use `not applicable: <file type>` as the symbol.
- A `code-change` event must include at least one `--file`.
- Every event with `--file` must also include `--symbol`.
- In each `code-change` body, include a concise description followed by the unified diff with hunk headers and three lines of context. For a new file, its complete content is acceptable as the diff.
- Record each command outcome as successful, failed, or blocked.
- For failures, record the cause and next safe step.
- Never rewrite or delete existing transcript history.
- Do not leave a trailing blank line at the end of a file.

## Event types

- `user-request`
- `user-addition`
- `user-decision`
- `agent-comment`
- `agent-response`
- `plan`
- `research`
- `decision`
- `action`
- `tool-call`
- `tool-result`
- `code-change`
- `verification`
- `error`
- `blocker`
- `commit`
- `push`
- `external-action`

## Commands

Show the current branch transcript:

```bash
python3 ~/.codex/skills/stenographer/scripts/stenographer.py show
```

Create a transcript:

```bash
python3 ~/.codex/skills/stenographer/scripts/stenographer.py init --task "Task description"
```

Record a user message:

```bash
python3 ~/.codex/skills/stenographer/scripts/stenographer.py append \
  --type user-request \
  --actor user \
  --title "Example" \
  --body "<complete verbatim user message>"
```

Record a code change:

```bash
python3 ~/.codex/skills/stenographer/scripts/stenographer.py append \
  --type code-change \
  --actor "Example Agent" \
  --title "Example" \
  --body "Example change.

@@ -1,3 +1,3 @@
 Example
-Old value
+New value
 Example" \
  --file "example/path/Example.ext" \
  --symbol "Example"
```

Record a verification:

```bash
python3 ~/.codex/skills/stenographer/scripts/stenographer.py append \
  --type verification \
  --actor "Example Agent" \
  --title "Example" \
  --command "example-command" \
  --result "Example result"
```

Resume work:

```bash
python3 ~/.codex/skills/stenographer/scripts/stenographer.py resume
```

Finish work:

```bash
python3 ~/.codex/skills/stenographer/scripts/stenographer.py finish --status "complete"
```

## Completing a response

Before the final response:

1. Confirm that every event from the current turn has been recorded.
2. If a final plan was produced, confirm that its complete content was recorded as a `plan` event.
3. Record the exact final response as an `agent-response` event.
4. Keep the final response self-contained; the transcript does not replace the user-facing response.
5. When branch work is complete, run `python3 ~/.codex/skills/stenographer/scripts/stenographer.py finish` to update the transcript status.