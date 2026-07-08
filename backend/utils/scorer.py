"""
scorer.py — Risk Scorer and Version Analyzer

This module compares the current version of a package to the latest version,
classifies the upgrade type (patch, minor, major), and calculates a risk
score using a rule-based formula. It also estimates upgrade confidence.

IMPORTANT: We use the 'packaging' library for all version comparisons.
Never compare version strings directly — "2.10" > "2.9" would be WRONG as a
string comparison because "10" < "9" alphabetically. The packaging library
handles this correctly.
"""

from packaging.version import Version, InvalidVersion  # Safe semantic version parsing
from packaging.specifiers import SpecifierSet, InvalidSpecifier  # For checking Python version compatibility
from datetime import datetime, timezone  # For checking how recently a package was updated


def analyze_and_score(
    current_version: str,
    latest_version: str,
    cves: list,
    pin_type: str,
    last_updated: str = None,
    all_versions: list = None
) -> dict:
    """
    Analyze version difference and calculate risk score for a package.

    This function is the decision-making brain of the advisor. It:
    1. Compares current vs latest version to determine upgrade type
    2. Calculates a numeric risk score using a rule-based formula
    3. Assigns a risk level label (Low, Medium, High)
    4. Estimates confidence in the recommendation

    The LLM (Gemini) NEVER makes these decisions — this function does.

    Args:
        current_version: The version currently in use (e.g., "2.3.1").
        latest_version: The newest version on PyPI (e.g., "3.0.0").
        cves: List of CVE IDs found for the current version.
        pin_type: How the version is pinned ("pinned", "minimum", or "unpinned").
        last_updated: ISO date string of when the latest version was released.
        all_versions: List of all version strings ever released.

    Returns:
        A dictionary with: upgrade_type, risk_score, risk_level, confidence_level.
    """
    # Default values — used if we can't parse the version strings
    upgrade_type = "unknown"
    risk_score = 0

    # ── Step 1: Parse versions using the 'packaging' library ──
    # Version("2.10") > Version("2.9") returns True (correct!)
    # whereas "2.10" > "2.9" returns False (wrong — string comparison!)
    try:
        current = Version(current_version) if current_version else None
        latest = Version(latest_version) if latest_version else None
    except InvalidVersion:
        # Some packages use non-standard version strings (e.g., "2.0rc1")
        # If we can't parse them, return safe defaults
        return {
            "upgrade_type": "unknown",
            "risk_score": 1,
            "risk_level": "Low",
            "confidence_level": "Low"
        }

    # ── Step 2: Determine upgrade type using semantic versioning ──
    # Semantic versioning format: MAJOR.MINOR.PATCH (e.g., 3.2.1)
    # - MAJOR change = likely breaking changes (2.x → 3.x)
    # - MINOR change = new features, usually backward compatible (2.3 → 2.4)
    # - PATCH change = bug fixes only, safest upgrade (2.3.1 → 2.3.2)
    if current and latest and latest > current:
        if latest.major > current.major:
            upgrade_type = "major"  # e.g., Django 3.x → Django 4.x
        elif latest.minor > current.minor:
            upgrade_type = "minor"  # e.g., Flask 2.2 → Flask 2.3
        else:
            upgrade_type = "patch"  # e.g., requests 2.28.1 → requests 2.28.2
    elif current and latest and latest == current:
        upgrade_type = "up-to-date"  # Already on the newest version
    else:
        upgrade_type = "unknown"  # Can't determine (missing version info)

    # ── Step 3: Calculate risk score using the rule-based formula ──
    # Each risk factor adds points. More points = higher risk.

    # Vulnerability found: +3 points (this is the most critical risk factor)
    if cves and len(cves) > 0:
        risk_score += 3

    # Major upgrade needed: +2 points (high chance of breaking changes)
    if upgrade_type == "major":
        risk_score += 2

    # Minor upgrade needed: +1 point (moderate risk of compatibility issues)
    if upgrade_type == "minor":
        risk_score += 1

    # Unpinned package: +1 point (version could change unpredictably)
    if pin_type == "unpinned":
        risk_score += 1

    # Patch-only upgrade: +0 points (very safe, just bug fixes)

    # ── Step 4: Map numeric score to a human-readable risk level ──
    if risk_score <= 1:
        risk_level = "Low"       # Score 0–1: Low priority, safe to leave for now
    elif risk_score <= 3:
        risk_level = "Medium"    # Score 2–3: Should upgrade soon
    else:
        risk_level = "High"      # Score 4+: Urgent — likely has CVEs + major upgrade

    # ── Step 5: Estimate confidence in our recommendation ──
    # High confidence = we have good data (CVEs, active releases, recent updates)
    # Low confidence = data is sparse or the package looks abandoned
    confidence_level = "High"  # Start optimistic, downgrade if we find issues

    # Check if the package hasn't been updated in over a year
    if last_updated:
        try:
            # Parse the upload timestamp from PyPI's format
            update_date = datetime.fromisoformat(
                last_updated.replace("Z", "+00:00")  # Handle UTC "Z" suffix
            )
            now = datetime.now(timezone.utc)
            days_since_update = (now - update_date).days

            # No update in 365+ days? The package might be abandoned
            if days_since_update > 365:
                confidence_level = "Low"
        except (ValueError, TypeError):
            # If we can't parse the date, we have less data to work with
            confidence_level = "Low"
    else:
        # No update date available at all — sparse metadata
        confidence_level = "Low"

    # Very few releases ever published — sparse history
    if all_versions and len(all_versions) < 3:
        confidence_level = "Low"

    # If we have CVE data AND version info, we have strong data → high confidence
    # CVE data is very reliable since it comes from security databases
    if cves and len(cves) > 0 and current and latest:
        confidence_level = "High"

    return {
        "upgrade_type": upgrade_type,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "confidence_level": confidence_level
    }


# ══════════════════════════════════════════════════════════════════════
# NEW: Check if a package version is compatible with the current Python
# ══════════════════════════════════════════════════════════════════════

def is_python_compatible(requires_python: str, current_python: str) -> bool:
    """
    Check if the current Python version satisfies a package's Python requirement.

    Uses packaging.specifiers.SpecifierSet to parse requirement strings like
    ">=3.8" or ">=3.7,<4.0" and check if the current Python version matches.

    We default to True (assume compatible) in these cases:
    - requires_python is empty or "Not specified"
    - The specifier string can't be parsed (malformed)

    This is safer than defaulting to False, which would incorrectly skip
    valid upgrade candidates.

    Args:
        requires_python: The requires_python string from PyPI (e.g., ">=3.8").
        current_python: The current Python version string (e.g., "3.9.7").

    Returns:
        True if compatible (or unknown), False if definitely incompatible.
    """
    # If no requirement is specified, assume compatible (most packages work broadly)
    if not requires_python or requires_python == "Not specified":
        return True

    try:
        # Parse the requirement specifier (e.g., ">=3.8" becomes a SpecifierSet)
        specifier = SpecifierSet(requires_python)
        # Check if the current Python version satisfies the requirement
        return Version(current_python) in specifier
    except (InvalidSpecifier, InvalidVersion):
        # If we can't parse either string, assume compatible to avoid
        # incorrectly skipping valid upgrade candidates
        return True


# ══════════════════════════════════════════════════════════════════════
# NEW: Find the minimum safe version to upgrade to (not the latest)
# ══════════════════════════════════════════════════════════════════════

def find_minimum_safe_version(
    package_name: str,
    current_version: str,
    all_versions: list,
    cves: list,
    current_python: str
) -> str:
    """
    Find the minimum (earliest) version newer than current that fixes known CVEs.

    Instead of always recommending the latest version (which could be a major
    upgrade with breaking changes), this function finds the FIRST version after
    the current one that's compatible with the user's Python version. This is
    the "minimum safe upgrade" — the smallest change needed to fix vulnerabilities.

    If no CVEs are found, returns None (no urgent upgrade needed).

    The function:
    1. Sorts all versions using packaging.version.Version (semantic ordering)
    2. Filters out versions older than or equal to the current version
    3. Checks each candidate's Python compatibility via get_python_requirement
    4. Returns the first compatible newer version

    Args:
        package_name: The package name (used to fetch Python requirements).
        current_version: The currently installed version string.
        all_versions: List of all version strings from PyPI.
        cves: List of CVE IDs found for the current version.
        current_python: The current Python version string (e.g., "3.9.7").

    Returns:
        The minimum safe version string, or None if no CVEs or no candidate found.
    """
    # Import here to avoid circular imports — fetcher is a sibling module
    from utils.fetcher import get_python_requirement

    # If no CVEs exist, there's no urgent need to find a minimum safe version
    if not cves or len(cves) == 0:
        return None

    # If we don't have version data, we can't determine a safe version
    if not current_version or not all_versions:
        return None

    try:
        # Parse the current version for comparison
        current = Version(current_version)
    except InvalidVersion:
        # Can't parse the current version — return None instead of crashing
        return None

    # Sort all versions using semantic versioning (not string sorting!)
    # This ensures "2.10" comes after "2.9", not before it
    sorted_versions = []
    for v_str in all_versions:
        try:
            sorted_versions.append((Version(v_str), v_str))  # Keep the original string too
        except InvalidVersion:
            # Skip versions with non-standard format (e.g., "2.0rc1")
            continue

    # Sort by the parsed Version objects (ascending order)
    sorted_versions.sort(key=lambda x: x[0])

    # Filter: only keep versions that are NEWER than the current version
    candidates = [(v, v_str) for v, v_str in sorted_versions if v > current]

    # Check each candidate version's Python compatibility, starting from the oldest
    for candidate_version, candidate_str in candidates:
        try:
            # Fetch the Python requirement for this specific version from PyPI
            requires_python = get_python_requirement(package_name, candidate_str)

            # Check if this version is compatible with the user's Python
            if is_python_compatible(requires_python, current_python):
                # Found the minimum safe version — return it
                return candidate_str
        except Exception:
            # If we can't check compatibility for this version, skip it
            # and try the next one instead of crashing
            continue

    # No compatible newer version found — return None
    return None

