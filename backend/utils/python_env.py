"""
python_env.py — Python Environment Utilities

This module provides functions to inspect the current Python environment.
It can detect the running Python version and list all installed packages
with their versions (via pip freeze).

These functions help the advisor check whether a package upgrade would be
compatible with the user's current Python version.
"""

import sys  # For reading the Python version info
import subprocess  # For running pip freeze as a shell command


# ══════════════════════════════════════════════════════════════════════
# FUNCTION 1: Get the current Python version
# ══════════════════════════════════════════════════════════════════════

def get_python_version() -> str:
    """
    Get the current Python interpreter version as a string.

    Uses sys.version_info to build a version string like "3.9.7".
    This is more reliable than parsing sys.version (which includes
    build info like "3.9.7 (default, Sep 16 2021, ...)").

    Returns:
        A version string in "major.minor.micro" format (e.g., "3.9.7").
    """
    # sys.version_info is a named tuple: (major, minor, micro, releaselevel, serial)
    # We only need the first three components for version checking
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


# ══════════════════════════════════════════════════════════════════════
# FUNCTION 2: Get all installed packages via pip freeze
# ══════════════════════════════════════════════════════════════════════

def get_installed_packages() -> dict:
    """
    Get a dictionary of all installed Python packages and their versions.

    Runs `pip freeze` as a subprocess and parses the output. Each line of
    pip freeze output looks like "package-name==1.2.3". We parse these into
    a dictionary with lowercase package names as keys and version strings
    as values.

    Returns:
        A dictionary like {"flask": "2.3.1", "django": "4.2.0", ...}.
        Returns an empty dict if pip freeze fails for any reason.
    """
    try:
        # Run pip freeze and capture its output
        # capture_output=True captures both stdout and stderr
        # text=True returns strings instead of bytes
        # timeout=30 prevents hanging if pip is stuck
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],  # Use the same Python that's running this script
            capture_output=True,
            text=True,
            timeout=30
        )

        packages = {}

        # Parse each line of pip freeze output
        for line in result.stdout.strip().split("\n"):
            line = line.strip()

            # Skip empty lines and lines that don't have the == separator
            if not line or "==" not in line:
                continue

            # Split "package-name==1.2.3" into name and version
            parts = line.split("==", 1)  # maxsplit=1 handles versions like "1.0==beta" (rare)
            if len(parts) == 2:
                name = parts[0].strip().lower()  # Normalize to lowercase for consistent lookup
                version = parts[1].strip()
                packages[name] = version

        return packages

    except subprocess.TimeoutExpired:
        # pip freeze took too long — return empty dict instead of crashing
        return {}

    except Exception as e:
        # Any other error (pip not found, permissions, etc.) — return empty dict
        return {}
