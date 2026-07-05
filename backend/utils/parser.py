"""
parser.py — Requirements.txt Parser

This module takes the raw text content of a Python requirements.txt file
and parses it into a structured list of package dictionaries. Each dictionary
contains the package name, its pinned version (if any), and the type of
version pin used (==, >=, or unpinned).
"""

import re  # Regular expressions for pattern matching in strings


def parse_requirements(file_content) -> list[dict]:
    """
    Parse raw requirements.txt content into a list of package info dictionaries.

    Takes the full text of a requirements.txt file and returns a list like:
    [{"name": "flask", "version": "2.3.1", "pin_type": "pinned"}, ...]

    Args:
        raw_text: The entire contents of a requirements.txt file as a string.

    Returns:
        A list of dictionaries, each with keys: name, version, pin_type.
    """
    # This list will hold our parsed package information
    packages = []

    for line in file_content.strip().split("\n"):
        line = line.strip()
        
        # Skip empty lines and comments
        if line == "" or line.startswith("#"):
            continue
        
        # If version is pinned exactly e.g. requests==2.28.1
        if "==" in line:
            parts = line.split("==")
            name = parts[0].strip()
            version = parts[1].strip()
            pin_type = "pinned"
        
        # If version has a minimum e.g. requests>=2.28.1
        elif ">=" in line:
            parts = line.split(">=")
            name = parts[0].strip()
            version = parts[1].strip()
            pin_type = "minimum"
        
        # If no version specified at all
        else:
            name = line.strip()
            version = "unknown"
            pin_type = "unpinned"
        
        # Add the package details to our list
        packages.append({
            "name": name,
            "version": version,
            "pin_type": pin_type
        })
    
    return packages