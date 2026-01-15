#!/usr/bin/env python3
"""
Direct MCP Server Debug - Raw output analysis
"""

import subprocess
import json

def debug_mcp_direct():
    """Debug MCP server raw output"""
    print("🔍 Direct MCP Server Debug")
    print("=" * 40)
    
    mcp_server_path = "./node_modules/@modelcontextprotocol/server-sequential-thinking/dist/index.js"
    
    # Test request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "sequentialthinking",
            "arguments": {
                "thought": "Break down workflow: get Gmail, visit website, take screenshot",
                "nextThoughtNeeded": True,
                "thoughtNumber": 1,
                "totalThoughts": 3
            }
        }
    }
    
    request_json = json.dumps(request)
    print(f"Request: {request_json[:100]}...")
    
    try:
        # Direct subprocess call
        result = subprocess.run(
            ["node", mcp_server_path],
            input=request_json,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"\nReturn code: {result.returncode}")
        print(f"STDOUT length: {len(result.stdout)}")
        print(f"STDERR length: {len(result.stderr)}")
        
        print(f"\nSTDOUT content:")
        print(f"'{result.stdout}'")
        
        print(f"\nSTDERR content:")
        print(f"'{result.stderr}'")
        
        # Try to find JSON in combined output
        all_output = result.stdout + "\n" + result.stderr
        lines = all_output.split('\n')
        
        print(f"\nAll lines ({len(lines)}):")
        for i, line in enumerate(lines):
            line_preview = line[:80] + "..." if len(line) > 80 else line
            print(f"{i:2}: '{line_preview}'")
        
        # Find JSON lines
        json_lines = []
        for i, line in enumerate(lines):
            line = line.strip()
            if line and line.startswith('{') and ('"jsonrpc"' in line or '"result"' in line):
                json_lines.append((i, line))
        
        print(f"\nJSON lines found: {len(json_lines)}")
        for line_num, json_content in json_lines:
            print(f"Line {line_num}: {json_content[:100]}...")
            
            # Try to parse
            try:
                parsed = json.loads(json_content)
                print(f"  ✅ Valid JSON")
                print(f"  Keys: {list(parsed.keys())}")
                if "result" in parsed:
                    content = parsed["result"].get("content", [])
                    print(f"  Content items: {len(content)}")
                    for item in content:
                        if item.get('type') == 'text':
                            text = item.get('text', '')
                            print(f"    Text preview: {text[:60]}...")
            except json.JSONDecodeError as e:
                print(f"  ❌ JSON Error: {e}")
        
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    debug_mcp_direct()