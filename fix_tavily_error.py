#!/usr/bin/env python3
"""
This script fixes the error in the TavilySearchRM class where it tries to access
an undefined 'result' variable in an exception handler and fixes the syntax error.
"""

import os

def fix_tavily_rm_error():
    rm_file_path = "./knowledge_storm/rm.py"
    
    with open(rm_file_path, 'r') as file:
        lines = file.readlines()
    
    # Find and fix the problematic lines
    for i, line in enumerate(lines):
        if "Error occurs when processing {result=" in line:
            lines[i] = line.replace("{result=}", "result")
        elif "Error occurs when processing result: {e}" in line and "\\n" not in line and "\n" not in line.rstrip("\n"):
            lines[i] = line.rstrip("\n") + "\n"
    
    # Write the modified content back to the file
    with open(rm_file_path, 'w') as file:
        file.writelines(lines)
    
    print("Fixed the TavilySearchRM error in knowledge_storm/rm.py")

if __name__ == "__main__":
    fix_tavily_rm_error()
