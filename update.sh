#!/bin/bash -ex
rsync -av ~/.claude/projects .
python3 jsonl_to_markdown.py -o projects_markdown --omit-user-commands --omit-tool-use --omit-tool-results --omit-function-calls
git add projects projects_markdown
