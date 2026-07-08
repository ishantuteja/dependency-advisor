"""
fetcher.py — PyPI Package Fetcher

This module talks to the PyPI (Python Package Index) JSON API to get
information about a Python package. It fetches the latest available version
and the full list of all versions ever released for that package.
"""

import httpx  # Modern async-capable HTTP client, similar to 'requests' but better


def fetch_pypi_info(package_name: str) -> dict:
    """
    Fetch package information from the PyPI JSON API.

    Calls https://pypi.org/pypi/{package_name}/json to get metadata about
    a Python package, including its latest version and full release history.

    Args:
        package_name: The name of the package to look up (e.g., "flask").

    Returns:
        A dictionary with:
            - latest_version: The most recent version string
            - all_versions: List of all version strings ever published
            - last_updated: ISO timestamp of when the latest release was uploaded
            - error: Error message string if something went wrong, None otherwise
    """
    # Build the URL for the PyPI JSON API endpoint
    url = f"https://pypi.org/pypi/{package_name}/json"

    try:
        # Make an HTTP GET request to PyPI with a 10-second timeout
        # The timeout prevents our program from hanging forever if PyPI is slow
        response = httpx.get(url, timeout=10.0, follow_redirects=True)

        # If the package doesn't exist on PyPI, the API returns a 404 status
        if response.status_code == 404:
            return {
                "latest_version": None,
                "all_versions": [],
                "last_updated": None,
                "error": f"Package '{package_name}' not found on PyPI"
            }

        # Raise an exception for any other HTTP error status (500, 403, etc.)
        response.raise_for_status()

        # Parse the JSON response body into a Python dictionary
        data = response.json()

        # The "info.version" field holds the latest stable version string
        latest_version = data.get("info", {}).get("version", None)

        # "releases" is a dict where keys are version strings and values are file lists
        # We only need the version strings (the dictionary keys)
        all_versions = list(data.get("releases", {}).keys())

        # Figure out when the latest version was last uploaded to PyPI
        # Each release version has a list of uploaded files with timestamps
        last_updated = None
        releases = data.get("releases", {})
        if latest_version and latest_version in releases:
            release_files = releases[latest_version]  # File uploads for latest version
            if release_files:
                # Use the upload_time of the first file as the release date
                last_updated = release_files[0].get("upload_time", None)

        return {
            "latest_version": latest_version,
            "all_versions": all_versions,
            "last_updated": last_updated,
            "error": None  # No error — everything worked fine
        }

    except httpx.TimeoutException:
        # The request took too long — PyPI might be overloaded or down
        return {
            "latest_version": None,
            "all_versions": [],
            "last_updated": None,
            "error": f"Timeout while fetching '{package_name}' from PyPI"
        }

    except httpx.HTTPError as e:
        # Some other HTTP-level error occurred (connection refused, bad gateway, etc.)
        return {
            "latest_version": None,
            "all_versions": [],
            "last_updated": None,
            "error": f"HTTP error fetching '{package_name}': {str(e)}"
        }

    except Exception as e:
        # Catch-all for any unexpected errors (network issues, JSON parse errors, etc.)
        return {
            "latest_version": None,
            "all_versions": [],
            "last_updated": None,
            "error": f"Unexpected error fetching '{package_name}': {str(e)}"
        }


# ══════════════════════════════════════════════════════════════════════
# NEW: Fetch the Python version requirement for a specific package version
# ══════════════════════════════════════════════════════════════════════

def get_python_requirement(package_name: str, version: str) -> str:
    """
    Fetch the requires_python field for a specific version of a package from PyPI.

    Calls https://pypi.org/pypi/{package_name}/{version}/json to get the
    version-specific metadata, then extracts the "requires_python" field.
    This tells us which Python versions are compatible with that package version
    (e.g., ">=3.8" means Python 3.8 or newer is required).

    Args:
        package_name: The name of the package (e.g., "flask").
        version: The specific version to check (e.g., "3.0.0").

    Returns:
        The requires_python string (e.g., ">=3.8"), or "Not specified" if
        the field is missing or the request fails.
    """
    # Build the version-specific PyPI URL — note the version in the path
    url = f"https://pypi.org/pypi/{package_name}/{version}/json"

    try:
        # Make the HTTP GET request with a 10-second timeout
        response = httpx.get(url, timeout=10.0, follow_redirects=True)

        # If this specific version doesn't exist on PyPI, return gracefully
        if response.status_code == 404:
            return "Not specified"

        # Raise for other HTTP errors (500, 403, etc.)
        response.raise_for_status()

        # Parse the response and extract the requires_python field
        data = response.json()
        requires_python = data.get("info", {}).get("requires_python")

        # If the field is missing or empty, return a clear default
        if not requires_python:
            return "Not specified"

        return requires_python

    except httpx.TimeoutException:
        # PyPI took too long — return safe default instead of crashing
        return "Not specified"

    except httpx.HTTPError:
        # HTTP-level error — return safe default
        return "Not specified"

    except Exception:
        # Any unexpected error — return safe default (never crash the pipeline)
        return "Not specified"
