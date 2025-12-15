# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This repository archives Claude Code session data from `~/.claude/projects` as both raw JSONL files and converted markdown files. The main tool is `jsonl_to_markdown.py`, which converts Claude session JSONL data into readable markdown format.

## Key Commands

### Update Session Data
```bash
./update.sh
```
This script:
1. Syncs JSONL files from `~/.claude/projects` to `./projects`
2. Converts all sessions to markdown (in `projects_markdown/`) with clean output (omitting tool use, tool results, function_calls, and user commands)
3. Stages the changes in git

### Convert Sessions to Markdown

Convert all sessions with default settings:
```bash
python3 jsonl_to_markdown.py
```

Convert with clean conversational output (recommended for reading):
```bash
python3 jsonl_to_markdown.py --omit-tool-use --omit-tool-results --omit-function-calls --omit-user-commands
```

Convert a single session file:
```bash
python3 jsonl_to_markdown.py -f projects/path/to/session.jsonl -o output_dir
```

Available filtering options:
- `--omit-tool-use`: Remove tool use blocks (the JSON showing tool calls)
- `--omit-tool-results`: Remove tool result blocks (the outputs from tools)
- `--omit-function-calls`: Strip `<function_calls>` XML blocks from text
- `--omit-user-commands`: Remove user command invocations like `/add-dir`, `/help`
- `--include-thinking`: Include thinking blocks (collapsed in `<details>` tags)

## Architecture

### Main Script: jsonl_to_markdown.py

The converter follows a simple pipeline:

1. **parse_jsonl_session()**: Reads JSONL file line by line, filters out meta messages and system output, extracts message content
2. **extract_text_from_content()**: Handles different content types (text, thinking, tool_use, tool_result) and applies filtering based on flags
3. **convert_to_markdown()**: Formats extracted messages as markdown with headers for User/Assistant sections
4. **process_jsonl_files()**: Orchestrates batch conversion of all JSONL files in a directory

### JSONL Format
Claude session files contain one JSON object per line with structure:
- `type`: "user" or "assistant" (or other types we skip)
- `message.role`: "user" or "assistant"
- `message.content`: String or array of content blocks (text, thinking, tool_use, tool_result)
- `timestamp`: ISO format timestamp
- `isMeta`: Boolean flag for metadata messages (skipped)

### Filtering Logic
- **Regex-based**: `<function_calls>` blocks removed via regex substitution
- **Type-based**: Tool use/results filtered by checking content block type
- **Pattern-based**: User commands detected by XML tag patterns (`<command-name>`, etc.)

## Directory Structure
- `projects/`: Raw JSONL session files (synced from `~/.claude/projects`)
- `projects_markdown/`: Converted markdown files
- `jsonl_to_markdown.py`: Main conversion script
- `update.sh`: Automation script for syncing and converting
