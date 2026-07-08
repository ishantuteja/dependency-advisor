"""
tools.py — LLM Agent Tool Definitions

This module defines the functions that the LLM agent can call as "tools."
In an agent architecture, tools are functions that the LLM can invoke to
gather information from external sources (like APIs).

These tools wrap the fetcher.py and vulnerability.py functions so they
can be registered as callable tools in the LangGraph agent workflow.
"""

from utils.fetcher import fetch_pypi_info
from utils.vulnerability import check_vulnerabilities
# NEW: Import the EOL checker for the new tool_check_eol function
from utils.eol_checker import check_eol_status


def tool_fetch_pypi(package_name: str) -> dict:
    """
    Tool: Fetch the latest version and release history of a Python package from PyPI.

    This tool calls the PyPI JSON API to retrieve metadata about a package,
    including its latest version number, all historical versions, and the
    date of the most recent release.

    Args:
        package_name: The name of the Python package to look up (e.g., "flask").

    Returns:
        A dictionary containing latest_version, all_versions, last_updated,
        and an error field (None if successful).
    """
    # Delegate to the actual fetcher function in utils/fetcher.py
    return fetch_pypi_info(package_name)


def tool_check_vulnerabilities(package_name: str, version: str) -> dict:
    """
    Tool: Check for known security vulnerabilities (CVEs) in a package version.

    This tool queries the OSV.dev API to find any known CVEs affecting the
    specified version of a Python package. OSV.dev aggregates vulnerability
    data from multiple security databases.

    Args:
        package_name: The name of the Python package (e.g., "django").
        version: The version string to check (e.g., "3.2.1").

    Returns:
        A dictionary containing a list of CVE IDs and an error field
        (None if successful).
    """
    # Delegate to the actual vulnerability checker in utils/vulnerability.py
    return check_vulnerabilities(package_name, version)


# ══════════════════════════════════════════════════════════════════════
# NEW TOOL: Check end-of-life status for a package
# ══════════════════════════════════════════════════════════════════════

def tool_check_eol(package_name: str) -> dict:
    """
    Tool: Check end-of-life status for a Python package.

    This tool queries the endoflife.date API to determine if a package
    has reached end-of-life or has a known EOL date approaching.
    Not all packages are tracked by endoflife.date — if the package
    isn't found, the result will indicate eol_available: False.

    Args:
        package_name: The name of the package to check (e.g., "django").

    Returns:
        A dictionary containing eol_available, eol_date, is_eol,
        days_until_eol, and a human-readable message.
    """
    # Delegate to the actual EOL checker in utils/eol_checker.py
    return check_eol_status(package_name)
