"""
eol_checker.py — End-of-Life and Activity Status Checker

This module provides three functions for assessing how "alive" a package is:

1. check_eol_status() — Queries the free endoflife.date API to check if a
   package has reached end-of-life or has a known EOL date coming up.

2. check_last_activity() — Calculates how recently a package was updated
   on PyPI and classifies its maintenance status.

3. get_upgrade_deadline() — Combines EOL info, risk level, and CVE data
   to suggest a concrete upgrade deadline with a date and urgency level.
"""

import httpx  # HTTP client for making API requests
from datetime import datetime, timezone, timedelta  # For date calculations


# ══════════════════════════════════════════════════════════════════════
# FUNCTION 1: Check End-of-Life status via endoflife.date API
# ══════════════════════════════════════════════════════════════════════

def check_eol_status(package_name: str) -> dict:
    """
    Check if a package has reached end-of-life using the endoflife.date API.

    Calls https://endoflife.date/api/{package_name}.json to get lifecycle data.
    The endoflife.date API tracks EOL dates for many popular software products.
    Not all Python packages are tracked — if the package isn't found (404),
    we return gracefully with eol_available: False.

    Args:
        package_name: The name of the package to check (e.g., "python", "django").

    Returns:
        A dictionary with eol_available, eol_date, is_eol, days_until_eol, and message.
    """
    # Build the API URL — endoflife.date uses the package name in the path
    url = f"https://endoflife.date/api/{package_name}.json"

    try:
        # Make an HTTP GET request with a 10-second timeout to avoid hanging
        response = httpx.get(url, timeout=10.0, follow_redirects=True)

        # If the package isn't tracked by endoflife.date, the API returns 404
        if response.status_code == 404:
            # Return gracefully — this is NOT an error, the package just isn't tracked
            return {
                "eol_available": False,
                "eol_date": None,
                "is_eol": False,
                "days_until_eol": None,
                "message": f"EOL data not available for '{package_name}' on endoflife.date"
            }

        # Raise an exception for any other HTTP error status (500, 403, etc.)
        response.raise_for_status()

        # Parse the JSON response — it returns a list of version cycles
        data = response.json()

        # The API returns a list of release cycles, newest first
        # We check the first (latest) cycle to get the most relevant EOL info
        if data and isinstance(data, list) and len(data) > 0:
            latest_cycle = data[0]  # The most recent release cycle

            # The "eol" field can be a date string ("2024-12-31") or a boolean (True/False)
            eol_value = latest_cycle.get("eol")

            # Determine if the package is EOL and when
            if isinstance(eol_value, bool):
                # Boolean EOL: True means already EOL, False means still supported
                return {
                    "eol_available": True,
                    "eol_date": None,  # No specific date when EOL is boolean
                    "is_eol": eol_value,
                    "days_until_eol": 0 if eol_value else None,
                    "message": "This version has reached end-of-life" if eol_value
                               else "This version is still supported"
                }
            elif isinstance(eol_value, str):
                # String EOL: a specific date like "2024-12-31"
                try:
                    eol_date = datetime.strptime(eol_value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    # Calculate days until EOL (negative means already past EOL)
                    days_until = (eol_date - now).days

                    is_eol = days_until < 0  # Negative days means EOL has passed

                    if is_eol:
                        message = f"End-of-life was reached on {eol_value} ({abs(days_until)} days ago)"
                    else:
                        message = f"End-of-life is on {eol_value} ({days_until} days remaining)"

                    return {
                        "eol_available": True,
                        "eol_date": eol_value,
                        "is_eol": is_eol,
                        "days_until_eol": days_until,
                        "message": message
                    }
                except (ValueError, TypeError):
                    # Could not parse the EOL date string — return safe defaults
                    return {
                        "eol_available": True,
                        "eol_date": eol_value,
                        "is_eol": False,
                        "days_until_eol": None,
                        "message": f"EOL date '{eol_value}' could not be parsed"
                    }

        # API returned an empty or unexpected response
        return {
            "eol_available": False,
            "eol_date": None,
            "is_eol": False,
            "days_until_eol": None,
            "message": "No lifecycle data found in API response"
        }

    except httpx.TimeoutException:
        # The endoflife.date API took too long — don't crash, return graceful default
        return {
            "eol_available": False,
            "eol_date": None,
            "is_eol": False,
            "days_until_eol": None,
            "message": f"Timeout checking EOL status for '{package_name}'"
        }

    except httpx.HTTPError as e:
        # Some HTTP error occurred (connection refused, bad gateway, etc.)
        return {
            "eol_available": False,
            "eol_date": None,
            "is_eol": False,
            "days_until_eol": None,
            "message": f"HTTP error checking EOL: {str(e)}"
        }

    except Exception as e:
        # Catch-all for any unexpected errors — never crash the pipeline
        return {
            "eol_available": False,
            "eol_date": None,
            "is_eol": False,
            "days_until_eol": None,
            "message": f"Unexpected error checking EOL: {str(e)}"
        }


# ══════════════════════════════════════════════════════════════════════
# FUNCTION 2: Check last activity / maintenance status of a package
# ══════════════════════════════════════════════════════════════════════

def check_last_activity(last_updated: str, all_versions: list) -> dict:
    """
    Determine how actively a package is maintained based on its update history.

    Takes the last_updated timestamp from PyPI and the list of all versions.
    Calculates days since the last update and classifies the maintenance status:
    - "Actively maintained" — updated within the last 90 days
    - "Slow maintenance"   — updated 90-365 days ago
    - "Possibly abandoned" — updated 1-2 years ago
    - "Likely abandoned"   — not updated in 2+ years

    Args:
        last_updated: ISO timestamp string from PyPI (e.g., "2024-01-15T10:30:00").
        all_versions: List of all version strings published for this package.

    Returns:
        A dictionary with days_since_last_update, total_versions_released, and activity_status.
    """
    # Count total versions — this gives a sense of the package's history
    total_versions = len(all_versions) if all_versions else 0

    # Default values if we can't calculate the update age
    if not last_updated:
        return {
            "days_since_last_update": None,
            "total_versions_released": total_versions,
            "activity_status": "Unknown"  # Can't determine without a date
        }

    try:
        # Parse the PyPI upload timestamp — handle the "Z" suffix for UTC
        update_date = datetime.fromisoformat(
            last_updated.replace("Z", "+00:00")
        )
        now = datetime.now(timezone.utc)

        # Calculate how many days ago the last update was
        days_since = (now - update_date).days

        # Classify the maintenance status based on the age threshold
        if days_since < 90:
            # Updated within 3 months — the package is actively worked on
            activity_status = "Actively maintained"
        elif days_since < 365:
            # Updated within the last year but not recently — slow but alive
            activity_status = "Slow maintenance"
        elif days_since < 730:
            # 1-2 years since last update — could be abandoned
            activity_status = "Possibly abandoned"
        else:
            # 2+ years with no update — very likely abandoned
            activity_status = "Likely abandoned"

        return {
            "days_since_last_update": days_since,
            "total_versions_released": total_versions,
            "activity_status": activity_status
        }

    except (ValueError, TypeError) as e:
        # Could not parse the timestamp — return safe defaults instead of crashing
        return {
            "days_since_last_update": None,
            "total_versions_released": total_versions,
            "activity_status": "Unknown"
        }


# ══════════════════════════════════════════════════════════════════════
# FUNCTION 3: Calculate an upgrade deadline based on EOL + risk + CVEs
# ══════════════════════════════════════════════════════════════════════

def get_upgrade_deadline(eol_info: dict, risk_level: str, cves: list) -> dict:
    """
    Suggest a concrete upgrade deadline by combining EOL, risk, and CVE data.

    The logic priority (highest to lowest):
    1. Already EOL → "Immediate" (Critical urgency)
    2. CVEs found → "Within 1 week" with actual date (High urgency)
    3. EOL within 90 days → "Before {eol_date}" (High urgency)
    4. High risk → "Within 1 month" (Medium urgency)
    5. Medium risk → "Within 2 months" (Medium urgency)
    6. Low risk → "Within 3 months" (Low urgency)

    Args:
        eol_info: Dictionary from check_eol_status() with is_eol, eol_date, etc.
        risk_level: The risk level string from the scorer ("High", "Medium", "Low").
        cves: List of CVE ID strings found for the package.

    Returns:
        A dictionary with deadline, deadline_date (YYYY-MM-DD), reason, and urgency.
    """
    now = datetime.now(timezone.utc)

    # Priority 1: Already past EOL — upgrade immediately
    if eol_info and eol_info.get("is_eol"):
        return {
            "deadline": "Immediate",
            "deadline_date": now.strftime("%Y-%m-%d"),  # Today's date
            "reason": "Package has reached end-of-life and no longer receives security patches",
            "urgency": "Critical"
        }

    # Priority 2: Known CVEs exist — upgrade within 1 week
    if cves and len(cves) > 0:
        one_week = now + timedelta(weeks=1)
        return {
            "deadline": "Within 1 week",
            "deadline_date": one_week.strftime("%Y-%m-%d"),
            "reason": f"{len(cves)} known vulnerability(ies) found — security risk",
            "urgency": "High"
        }

    # Priority 3: EOL is coming within 90 days — upgrade before the EOL date
    if eol_info and eol_info.get("days_until_eol") is not None:
        days_until = eol_info["days_until_eol"]
        if 0 < days_until <= 90:
            return {
                "deadline": f"Before {eol_info.get('eol_date', 'EOL date')}",
                "deadline_date": eol_info.get("eol_date", (now + timedelta(days=days_until)).strftime("%Y-%m-%d")),
                "reason": f"End-of-life in {days_until} days — plan migration now",
                "urgency": "High"
            }

    # Priority 4: High risk score (major version gap, etc.) — upgrade within 1 month
    if risk_level == "High":
        one_month = now + timedelta(days=30)
        return {
            "deadline": "Within 1 month",
            "deadline_date": one_month.strftime("%Y-%m-%d"),
            "reason": "High risk level — significant version gap or compatibility concerns",
            "urgency": "Medium"
        }

    # Priority 5: Medium risk — upgrade within 2 months
    if risk_level == "Medium":
        two_months = now + timedelta(days=60)
        return {
            "deadline": "Within 2 months",
            "deadline_date": two_months.strftime("%Y-%m-%d"),
            "reason": "Medium risk level — upgrade recommended to stay current",
            "urgency": "Medium"
        }

    # Priority 6: Low risk or default — upgrade within 3 months (no rush)
    three_months = now + timedelta(days=90)
    return {
        "deadline": "Within 3 months",
        "deadline_date": three_months.strftime("%Y-%m-%d"),
        "reason": "Low risk — upgrade at your convenience during regular maintenance",
        "urgency": "Low"
    }
