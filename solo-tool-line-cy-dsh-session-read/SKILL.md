---
name: solo-tool-line-cy-dsh-session-read
description: "读取并检索 DeepSeek Harness（DSH）会话归档——存放在 C:\\Users\\admin\\.dsh\\sessions 下、zstd 压缩的 JSONL 全量记录。用于续接先前会话的工作、找回因压缩丢失的上下文、查某个历史会话决定了什么或做了什么、定位旧对话中提到的文件或路径、构建跨会话时间线，或回答「第 X 个会话里我们干了啥」。对本机每个工作区的每个历史会话都有效，同一脚本也可由子代理调用。"
---

# Read DSH Session Archives

## Where archives live

```
C:\Users\admin\.dsh\sessions\<encoded-workspace>\session-<uuid>\session.v4.jsonl.zstd
```

The workspace dir name is the full workspace path encoded: separators become `-`, non-ASCII becomes `~<4-hex-codepoints>`. Example: `--D-ai~0020program-~4E34~65F6dsh--` = `D:\ai program\临时dsh`. Never hand-decode - the script fuzzy-matches by `--workspace`.

## Read with the bundled script

```powershell
$env:PYTHONIOENCODING='utf8'
& 'C:\Users\admin\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe' `
  'C:\Users\admin\.claude\skills\solo-tool-line-cy-dsh-session-read\scripts\read_session.py' `
  --workspace 临时dsh --grep 存档 --last 20
```

Parameters:

- `--list-sessions` - list every workspace + session id + archive size; start here when unsure
- `--workspace <kw>` - fuzzy-match the encoded dir (Chinese works, matches decoded name)
- `--session <uuid-fragment>` - filter by session id
- `--role user|assistant|tool|all` - default `all`; `tool` = `tool/call` rows
- `--grep <kw>` - keyword inside extracted message text or event type
- `--since <ts>` / `--until <ts>` — time range, accepts epoch milliseconds or ISO datetime (e.g. `2026-11-02` for "that day onward")
- `--last N` - keep last N matches (default 20)
- `--max-len N` - truncate extracted text (default 280 chars)
- `--stats` - print event-type counts for the session instead of rows
- `--show-json` - print raw JSON rows instead of extracted text

Workflow: start with `--list-sessions`, then narrow with `--workspace` + `--role` + `--grep`, widen `--last` only if needed. Set `$env:PYTHONIOENCODING='utf8'` if output shows mojibake.

## Format notes (v4)

Each line is one event: `{seq, time, type, data, ...}`. Key types: `user/message` and `assistant/message` (full conversation texts), `tool/call` + `tool/result`, `turn/start|end`, `step/start|end`, `session` (cwd, createdAt), `session/title`, `permission/*`, `approval/*`, `todo/write`, `command/*`. Message text lives somewhere inside `data` - the script auto-extracts the most informative string; if an extraction looks wrong, rerun that row with `--show-json` and read `data` directly.

## Boundaries

- The format tag is `v4` and may change with a DSH update. If decompression yields nothing parseable, check the sessions dir for a newer filename pattern before assuming data loss.
- Archives contain full conversations and tool outputs - sensitive. Quote narrowly into answers; never dump wholesale into reports or send content off-machine.
- Dependency: `zstandard` in the bundled Python at `C:\Users\admin\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\` (already installed; reinstall with `python -m pip install zstandard`).
