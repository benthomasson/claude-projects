#!/usr/bin/env python3
"""
Convert Claude session JSONL data to markdown format.
"""

import json
import os
import argparse
import re
from pathlib import Path
from datetime import datetime


def extract_text_from_content(content, include_thinking=False, omit_tool_use=False, omit_tool_results=False, omit_function_calls=False):
    """Extract readable text from message content."""
    if isinstance(content, str):
        text = content
        # Remove function_calls blocks if requested
        if omit_function_calls:
            text = re.sub(r'<function_calls>.*?</function_calls>', '', text, flags=re.DOTALL)
            text = text.strip()
        return text

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    text = item.get('text', '')
                    # Remove function_calls blocks if requested
                    if omit_function_calls:
                        text = re.sub(r'<function_calls>.*?</function_calls>', '', text, flags=re.DOTALL)
                        text = text.strip()
                    if text:
                        text_parts.append(text)
                elif item.get('type') == 'thinking':
                    # Optionally include thinking blocks
                    if include_thinking:
                        thinking = item.get('thinking', '')
                        if thinking:
                            text_parts.append(f"<details><summary>💭 Thinking</summary>\n\n{thinking}\n\n</details>")
                elif item.get('type') == 'tool_use':
                    # Format tool use (unless omitted)
                    if not omit_tool_use:
                        tool_name = item.get('name', 'unknown')
                        tool_input = json.dumps(item.get('input', {}), indent=2)
                        text_parts.append(f"**Tool Use: {tool_name}**\n```json\n{tool_input}\n```")
                elif item.get('type') == 'tool_result':
                    # Format tool results (unless omitted)
                    if not omit_tool_results:
                        tool_result = item.get('content', '')
                        if isinstance(tool_result, str):
                            text_parts.append(f"**Tool Result:**\n```\n{tool_result}\n```")
                        else:
                            text_parts.append(f"**Tool Result:**\n```json\n{json.dumps(tool_result, indent=2)}\n```")
            elif isinstance(item, str):
                text = item
                # Remove function_calls blocks if requested
                if omit_function_calls:
                    text = re.sub(r'<function_calls>.*?</function_calls>', '', text, flags=re.DOTALL)
                    text = text.strip()
                if text:
                    text_parts.append(text)
        return '\n\n'.join(text_parts)

    return str(content)


def parse_jsonl_session(jsonl_path, include_thinking=False, omit_tool_use=False, omit_user_commands=False, omit_tool_results=False, omit_function_calls=False):
    """Parse a JSONL session file and extract messages."""
    messages = []

    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())

                # Skip non-message types
                if data.get('type') not in ['user', 'assistant']:
                    continue

                # Skip meta messages
                if data.get('isMeta', False):
                    continue

                msg = data.get('message', {})
                role = msg.get('role')
                content = msg.get('content', '')
                timestamp = data.get('timestamp', '')

                # Extract text content
                text = extract_text_from_content(content, include_thinking, omit_tool_use, omit_tool_results, omit_function_calls)

                # Filter out empty messages and system commands
                if not text or text.strip() == '':
                    continue

                # Skip local command outputs and caveats
                if '<local-command-stdout>' in text or 'Caveat:' in text:
                    continue

                # Skip user command invocations if requested
                if omit_user_commands and role == 'user':
                    if '<command-name>' in text or '<command-message>' in text or '<command-args>' in text:
                        continue

                messages.append({
                    'role': role,
                    'content': text,
                    'timestamp': timestamp,
                    'uuid': data.get('uuid', '')
                })

            except json.JSONDecodeError:
                continue

    return messages


def convert_to_markdown(messages, session_name, output_path):
    """Convert messages to markdown format."""
    md_lines = [f"# {session_name}\n"]

    if messages:
        first_ts = messages[0].get('timestamp', '')
        if first_ts:
            dt = datetime.fromisoformat(first_ts.replace('Z', '+00:00'))
            md_lines.append(f"*Session Date: {dt.strftime('%Y-%m-%d %H:%M:%S')}*\n")

    md_lines.append("---\n")

    for i, msg in enumerate(messages, 1):
        role = msg['role']
        content = msg['content']

        if role == 'user':
            md_lines.append(f"## User\n\n{content}\n")
        elif role == 'assistant':
            md_lines.append(f"## Assistant\n\n{content}\n")

        md_lines.append("\n---\n")

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))


def process_jsonl_files(projects_dir, output_dir, include_thinking=False, omit_tool_use=False, omit_user_commands=False, omit_tool_results=False, omit_function_calls=False):
    """Process all JSONL files in the projects directory."""
    projects_path = Path(projects_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    jsonl_files = list(projects_path.rglob('*.jsonl'))

    print(f"Found {len(jsonl_files)} JSONL files")

    for jsonl_file in jsonl_files:
        # Skip agent session files
        if jsonl_file.name.startswith('agent-'):
            print(f"Skipping agent file: {jsonl_file.name}")
            continue

        # Create output filename
        relative_path = jsonl_file.relative_to(projects_path)
        session_name = str(relative_path.parent / relative_path.stem)

        # Parse messages
        messages = parse_jsonl_session(jsonl_file, include_thinking, omit_tool_use, omit_user_commands, omit_tool_results, omit_function_calls)

        if not messages:
            print(f"Skipping {jsonl_file.name} (no messages)")
            continue

        # Create output path
        output_file = output_path / f"{relative_path.parent.name}_{relative_path.stem}.md"

        # Convert to markdown
        convert_to_markdown(messages, session_name, output_file)
        print(f"Converted {jsonl_file.name} -> {output_file.name} ({len(messages)} messages)")


def main():
    parser = argparse.ArgumentParser(description='Convert Claude session JSONL to Markdown')
    parser.add_argument('--projects-dir', '-p', default='./projects',
                        help='Directory containing JSONL session files (default: ./projects)')
    parser.add_argument('--output-dir', '-o', default='./markdown_sessions',
                        help='Output directory for markdown files (default: ./markdown_sessions)')
    parser.add_argument('--include-thinking', action='store_true',
                        help='Include thinking blocks in the output')
    parser.add_argument('--omit-tool-use', action='store_true',
                        help='Omit tool use blocks from the output')
    parser.add_argument('--omit-tool-results', action='store_true',
                        help='Omit tool result blocks from the output')
    parser.add_argument('--omit-function-calls', action='store_true',
                        help='Omit function_calls XML blocks from the output')
    parser.add_argument('--omit-user-commands', action='store_true',
                        help='Omit user command invocations from the output')
    parser.add_argument('--single-file', '-f',
                        help='Convert a single JSONL file instead of scanning directory')

    args = parser.parse_args()

    if args.single_file:
        # Convert single file
        jsonl_path = Path(args.single_file)
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        messages = parse_jsonl_session(jsonl_path, args.include_thinking, args.omit_tool_use, args.omit_user_commands, args.omit_tool_results, args.omit_function_calls)
        output_file = output_path / f"{jsonl_path.stem}.md"

        convert_to_markdown(messages, jsonl_path.stem, output_file)
        print(f"Converted {jsonl_path.name} -> {output_file.name} ({len(messages)} messages)")
    else:
        # Process all files in directory
        process_jsonl_files(args.projects_dir, args.output_dir, args.include_thinking, args.omit_tool_use, args.omit_user_commands, args.omit_tool_results, args.omit_function_calls)


if __name__ == '__main__':
    main()
