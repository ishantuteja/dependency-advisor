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
