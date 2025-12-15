# Claude Projects

A backup of all claude interactions

## JSONL to Markdown Converter

This repository includes a Python script (`jsonl_to_markdown.py`) that converts Claude Code session data from JSONL format to readable Markdown files.

### Features

- Converts JSONL session files to formatted Markdown
- Extracts user prompts and assistant responses
- Optionally includes thinking blocks (collapsed in details tags)
- Optionally shows or omits tool use blocks, tool results, and function_calls XML blocks
- Optionally filters out user command invocations (e.g., `/add-dir`, `/help`)
- Shows tool use and results with formatted JSON
- Filters out system messages and meta content
- Processes single files or entire directories

### Usage

#### Convert All Sessions in Projects Directory

```bash
python3 jsonl_to_markdown.py
```

This will:
- Read all `.jsonl` files from `./projects/`
- Output markdown files to `./markdown_sessions/`

#### Convert a Single File

```bash
python3 jsonl_to_markdown.py -f path/to/session.jsonl
```

#### Custom Directories

```bash
python3 jsonl_to_markdown.py --projects-dir ./my-sessions --output-dir ./my-output
```

#### Include Thinking Blocks

By default, thinking blocks are not included. To include them in the output:

```bash
python3 jsonl_to_markdown.py --include-thinking
```

#### Omit Tool Use

To create a cleaner output without tool use blocks:

```bash
python3 jsonl_to_markdown.py --omit-tool-use
```

#### Omit Tool Results

To filter out tool result blocks (function call results):

```bash
python3 jsonl_to_markdown.py --omit-tool-results
```

#### Omit Function Calls

To remove `<function_calls>` XML blocks from the text:

```bash
python3 jsonl_to_markdown.py --omit-function-calls
```

#### Omit User Commands

To filter out user command invocations (like `/add-dir`, `/help`, etc.):

```bash
python3 jsonl_to_markdown.py --omit-user-commands
```

### Options

- `-p, --projects-dir`: Directory containing JSONL session files (default: `./projects`)
- `-o, --output-dir`: Output directory for markdown files (default: `./markdown_sessions`)
- `-f, --single-file`: Convert a single JSONL file instead of scanning directory
- `--include-thinking`: Include thinking blocks in the output (shown in collapsible sections)
- `--omit-tool-use`: Omit tool use blocks from the output
- `--omit-tool-results`: Omit tool result blocks from the output
- `--omit-function-calls`: Omit function_calls XML blocks from the output
- `--omit-user-commands`: Omit user command invocations from the output

### Output Format

The generated markdown files include:

- Session name as heading
- Session date/time
- Alternating User and Assistant sections
- Tool use formatted as JSON code blocks
- Thinking blocks in collapsible `<details>` tags

### Example

```bash
# Convert all sessions
python3 jsonl_to_markdown.py

# Convert one session
python3 jsonl_to_markdown.py -f ./projects/-Users-ai-git-space-game2/6df1a891-9fa5-493c-b7d2-7b0f75ebac62.jsonl

# Convert with custom output directory
python3 jsonl_to_markdown.py -o ./exported-sessions

# Convert without tool use for cleaner reading
python3 jsonl_to_markdown.py --omit-tool-use

# Convert without tool results
python3 jsonl_to_markdown.py --omit-tool-results

# Convert without function_calls XML blocks
python3 jsonl_to_markdown.py --omit-function-calls

# Convert without user commands
python3 jsonl_to_markdown.py --omit-user-commands

# Combine options for cleanest output (conversation only)
python3 jsonl_to_markdown.py --omit-tool-use --omit-tool-results --omit-function-calls --omit-user-commands

# Convert with thinking blocks included
python3 jsonl_to_markdown.py --include-thinking
```

### Requirements

- Python 3.6+
- No external dependencies required (uses only standard library)
