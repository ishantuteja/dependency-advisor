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
