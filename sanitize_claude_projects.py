#!/usr/bin/env python3

"""
Sanitize claude-projects JSON exports to remove sensitive information
that would trigger rh-gitleaks security checks.

This script removes:
- Private keys (BEGIN PRIVATE KEY ... END PRIVATE KEY)
- Certificates (BEGIN CERTIFICATE ... END CERTIFICATE) 
- SSH keys (BEGIN OPENSSH PRIVATE KEY ... END OPENSSH PRIVATE KEY)
- API tokens and other sensitive patterns
- Consumer UUIDs and other identifiers

Usage:
    python3 sanitize_claude_projects.py input.json output.json
    python3 sanitize_claude_projects.py --in-place file.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Sensitive patterns to remove or redact
SENSITIVE_PATTERNS = [
    # Private keys
    (r'-----BEGIN PRIVATE KEY-----.*?-----END PRIVATE KEY-----', '[PRIVATE KEY REDACTED]'),
    (r'-----BEGIN RSA PRIVATE KEY-----.*?-----END RSA PRIVATE KEY-----', '[RSA PRIVATE KEY REDACTED]'),
    (r'-----BEGIN OPENSSH PRIVATE KEY-----.*?-----END OPENSSH PRIVATE KEY-----', '[SSH PRIVATE KEY REDACTED]'),
    (r'-----BEGIN EC PRIVATE KEY-----.*?-----END EC PRIVATE KEY-----', '[EC PRIVATE KEY REDACTED]'),
    
    # Certificates (sometimes contain sensitive info)
    (r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', '[CERTIFICATE REDACTED]'),
    (r'-----BEGIN X509 CERTIFICATE-----.*?-----END X509 CERTIFICATE-----', '[X509 CERTIFICATE REDACTED]'),
    
    # API tokens and keys
    (r'["\']?token["\']?\s*:\s*["\'][^"\']+["\']', '"token": "[TOKEN REDACTED]"'),
    (r'["\']?api_?key["\']?\s*:\s*["\'][^"\']+["\']', '"api_key": "[API KEY REDACTED]"'),
    (r'["\']?access_?token["\']?\s*:\s*["\'][^"\']+["\']', '"access_token": "[ACCESS TOKEN REDACTED]"'),
    
    # Consumer UUIDs (specific to our project)
    #(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '[UUID REDACTED]'),
    
    # Passwords and secrets
    (r'["\']?password["\']?\s*:\s*["\'][^"\']+["\']', '"password": "[PASSWORD REDACTED]"'),
    (r'["\']?secret["\']?\s*:\s*["\'][^"\']+["\']', '"secret": "[SECRET REDACTED]"'),
    
    # File paths that might contain sensitive info
    #(r'/etc/pki/consumer/[^"\'\\s]+', '[PKI PATH REDACTED]'),
    #(r'/home/[^/]+/\.ssh/[^"\'\\s]+', '[SSH PATH REDACTED]'),
    
    # Email addresses (might be considered PII)
    #(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL REDACTED]'),
    
    # IP addresses (might be internal)
    #(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP REDACTED]'),
    
    # Common secret environment variables
    (r'[A-Z_]*(?:TOKEN|KEY|SECRET|PASSWORD|AUTH)[A-Z_]*=[^"\'\\s]+', '[ENV SECRET REDACTED]'),
    
    # AWS-specific patterns
    (r'AKIA[0-9A-Z]{16}', '[AWS ACCESS KEY REDACTED]'),  # AWS Access Key ID format
    (r'[A-Za-z0-9/+=]{40}', '[AWS SECRET KEY REDACTED]'),  # AWS Secret Access Key (40 chars base64-like)
    (r'aws_access_key_id\s*[=:]\s*["\']?[A-Z0-9]{20}["\']?', 'aws_access_key_id = "[AWS ACCESS KEY REDACTED]"'),
    (r'aws_secret_access_key\s*[=:]\s*["\']?[A-Za-z0-9/+=]{40}["\']?', 'aws_secret_access_key = "[AWS SECRET KEY REDACTED]"'),
    (r'aws_session_token\s*[=:]\s*["\']?[A-Za-z0-9/+=]+["\']?', 'aws_session_token = "[AWS SESSION TOKEN REDACTED]"'),
    
    # AWS ARN patterns (might contain account numbers)
    (r'arn:aws:[^:]*:[^:]*:\d{12}:[^"\'\\s]+', '[AWS ARN REDACTED]'),
    
    # AWS Account ID (12 digits)
    (r'\b\d{12}\b', '[AWS ACCOUNT ID REDACTED]'),
    
    # AWS Region-specific endpoints with account info
    (r'https://[a-z0-9\-]+\.execute-api\.[a-z0-9\-]+\.amazonaws\.com/[^"\'\\s]*', '[AWS API GATEWAY ENDPOINT REDACTED]'),
    (r'https://[a-z0-9\-]+\.s3\.[a-z0-9\-]+\.amazonaws\.com/[^"\'\\s]*', '[AWS S3 ENDPOINT REDACTED]'),
    
    # Lambda function names that might be sensitive
    (r'"FunctionName"\s*:\s*"[^"]*"', '"FunctionName": "[LAMBDA FUNCTION REDACTED]"'),
    
    # DynamoDB table names
    (r'"TableName"\s*:\s*"[^"]*"', '"TableName": "[DYNAMODB TABLE REDACTED]"'),
    
    # AWS Certificate ARNs
    (r'arn:aws:acm:[^:]*:[^:]*:certificate/[a-f0-9\-]+', '[AWS CERTIFICATE ARN REDACTED]'),
    
    # AWS IAM Role ARNs
    (r'arn:aws:iam::\d{12}:role/[^"\'\\s]+', '[AWS IAM ROLE ARN REDACTED]'),
    
    # AWS CloudFormation Stack names (might be sensitive)
    (r'"StackName"\s*:\s*"[^"]*"', '"StackName": "[CLOUDFORMATION STACK REDACTED]"'),
]

def sanitize_text(text):
    """Remove or redact sensitive patterns from text."""
    if not isinstance(text, str):
        return text
    
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.DOTALL | re.IGNORECASE)
    
    return result

def sanitize_json_recursive(obj):
    """Recursively sanitize a JSON object."""
    if isinstance(obj, dict):
        return {key: sanitize_json_recursive(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_json_recursive(item) for item in obj]
    elif isinstance(obj, str):
        return sanitize_text(obj)
    else:
        return obj

def detect_file_format(input_path):
    """Detect if file is JSON or JSONL format."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if not first_line:
                return 'empty'
            
            # Try to parse first line as JSON
            json.loads(first_line)
            
            # Check if there are more lines
            second_line = f.readline().strip()
            if second_line:
                # Try to parse second line as JSON too
                json.loads(second_line)
                return 'jsonl'  # Multiple valid JSON lines = JSONL
            else:
                return 'json'   # Single JSON object
                
    except json.JSONDecodeError:
        # If first line isn't valid JSON, try parsing whole file as JSON
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return 'json'
        except json.JSONDecodeError:
            return 'unknown'
    except Exception:
        return 'unknown'

def sanitize_jsonl_file(input_path, output_path=None):
    """Sanitize a JSONL (JSON Lines) file."""
    input_path = Path(input_path)
    
    if output_path is None:
        output_path = input_path
    else:
        output_path = Path(output_path)
    
    lines_processed = 0
    redaction_count = 0
    total_size = 0
    
    try:
        with open(input_path, 'r', encoding='utf-8') as infile, \
             open(output_path, 'w', encoding='utf-8') as outfile:
            
            for line_num, line in enumerate(infile, 1):
                line = line.strip()
                if not line:  # Skip empty lines
                    outfile.write('\n')
                    continue
                
                try:
                    # Parse JSON line
                    json_obj = json.loads(line)
                    original_text = json.dumps(json_obj)
                    total_size += len(original_text)
                    
                    # Sanitize the JSON object
                    sanitized_obj = sanitize_json_recursive(json_obj)
                    sanitized_text = json.dumps(sanitized_obj)
                    
                    # Count redactions in this line
                    line_redactions = sum(sanitized_text.count(replacement) for _, replacement in SENSITIVE_PATTERNS)
                    redaction_count += line_redactions
                    
                    # Write sanitized JSON line
                    outfile.write(json.dumps(sanitized_obj, ensure_ascii=False) + '\n')
                    lines_processed += 1
                    
                except json.JSONDecodeError as e:
                    print(f"Warning: Line {line_num} is not valid JSON: {e}", file=sys.stderr)
                    # Write line as-is but sanitize as text
                    sanitized_line = sanitize_text(line)
                    outfile.write(sanitized_line + '\n')
                    
        print(f"✅ Processed {lines_processed} JSON lines ({total_size // 1024} KB)")
        
        if redaction_count > 0:
            print(f"🔒 Redacted {redaction_count} sensitive items")
        else:
            print("ℹ️  No sensitive content detected")
            
        return True
        
    except Exception as e:
        print(f"Error processing JSONL file {input_path}: {e}", file=sys.stderr)
        return False

def sanitize_json_file(input_path, output_path=None):
    """Sanitize a regular JSON file."""
    input_path = Path(input_path)
    
    if output_path is None:
        output_path = input_path
    else:
        output_path = Path(output_path)
    
    try:
        # Load JSON
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Loaded JSON file {input_path} ({len(json.dumps(data)) // 1024} KB)")
        
        # Sanitize recursively
        sanitized_data = sanitize_json_recursive(data)
        
        # Write sanitized data
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sanitized_data, f, indent=2, ensure_ascii=False)
        
        sanitized_size = len(json.dumps(sanitized_data)) // 1024
        print(f"✅ Sanitized and saved to {output_path} ({sanitized_size} KB)")
        
        # Count redactions
        original_text = json.dumps(data)
        sanitized_text = json.dumps(sanitized_data)
        redaction_count = sum(sanitized_text.count(replacement) for _, replacement in SENSITIVE_PATTERNS)
        
        if redaction_count > 0:
            print(f"🔒 Redacted {redaction_count} sensitive items")
        else:
            print("ℹ️  No sensitive content detected")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {input_path}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error processing {input_path}: {e}", file=sys.stderr)
        return False

def sanitize_file(input_path, output_path=None):
    """Sanitize a claude-projects file (auto-detect JSON vs JSONL format)."""
    input_path = Path(input_path)
    
    if not input_path.exists():
        print(f"Error: Input file {input_path} does not exist", file=sys.stderr)
        return False
    
    # Auto-detect file format
    file_format = detect_file_format(input_path)
    
    if file_format == 'jsonl':
        print(f"📝 Detected JSONL format (JSON Lines)")
        return sanitize_jsonl_file(input_path, output_path)
    elif file_format == 'json':
        print(f"📝 Detected JSON format")
        return sanitize_json_file(input_path, output_path)
    elif file_format == 'empty':
        print(f"⚠️  File is empty")
        if output_path and output_path != input_path:
            # Copy empty file
            output_path.touch()
        return True
    else:
        print(f"❌ Unable to detect valid JSON/JSONL format in {input_path}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Sanitize claude-projects JSON files to remove sensitive information'
    )
    parser.add_argument(
        'input_file',
        help='Input JSON file to sanitize'
    )
    parser.add_argument(
        'output_file',
        nargs='?',
        help='Output file (default: same as input for in-place editing)'
    )
    parser.add_argument(
        '--in-place',
        action='store_true',
        help='Edit file in place (same as not specifying output_file)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be redacted without writing output'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed redaction information'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.output_file and args.in_place:
        print("Error: Cannot specify both output_file and --in-place", file=sys.stderr)
        sys.exit(1)
    
    output_file = args.output_file if not args.in_place else None
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
        # Load and show what would be redacted
        try:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            original_text = json.dumps(data)
            sanitized_data = sanitize_json_recursive(data)
            sanitized_text = json.dumps(sanitized_data)
            
            if args.verbose:
                for pattern, replacement in SENSITIVE_PATTERNS:
                    matches = re.findall(pattern, original_text, flags=re.DOTALL | re.IGNORECASE)
                    if matches:
                        print(f"Would redact {len(matches)} instances matching: {pattern}")
                        if args.verbose:
                            for i, match in enumerate(matches[:3]):  # Show first 3
                                preview = match[:50] + "..." if len(match) > 50 else match
                                print(f"  {i+1}. {preview}")
            
            redaction_count = sum(sanitized_text.count(replacement) for _, replacement in SENSITIVE_PATTERNS)
            print(f"Total redactions: {redaction_count}")
            
        except Exception as e:
            print(f"Error in dry run: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Perform actual sanitization
        success = sanitize_file(args.input_file, output_file)
        if not success:
            sys.exit(1)
        
        print("\n✅ Sanitization complete!")
        print("🔒 This file should now pass rh-gitleaks security checks")
        print("⚠️  Review the output to ensure no legitimate content was over-redacted")

if __name__ == '__main__':
    main()
