"""
agent.py — LangGraph Workflow Definition

This module defines the LangGraph agent workflow that orchestrates the
entire dependency analysis pipeline. Here's the execution order:

    1. PARSE node runs first (extracts packages from requirements.txt)
    2. FETCH + VULN nodes run IN PARALLEL (this is why we use LangGraph —
       it supports parallel node execution natively, unlike plain LangChain)
    3. SCORE node runs next (analyzes versions and calculates risk)
    4. NARRATE node runs last (Gemini generates human-readable recommendations)

All nodes share a single state object that they read from and write to.
This shared state is how data flows between pipeline stages.
"""

import os  # For reading environment variables (like the API key)
from typing import TypedDict, Annotated  # For defining the shared state schema
import operator  # For the list-merge strategy in parallel nodes

from langgraph.graph import StateGraph, START, END  # LangGraph core components
from google import genai  # Google's Gemini SDK for LLM calls

# Import our custom modules
from utils.parser import parse_requirements
from utils.scorer import analyze_and_score, find_minimum_safe_version
from tools import tool_fetch_pypi, tool_check_vulnerabilities
from prompt import RECOMMENDATION_PROMPT, WHAT_BREAKS_PROMPT, COMBINED_ANALYSIS_PROMPT

# NEW: Import EOL checker functions for the enhanced score_node
from utils.eol_checker import check_eol_status, check_last_activity, get_upgrade_deadline
# NEW: Import Python environment utility for version checking
from utils.python_env import get_python_version


# ══════════════════════════════════════════════════════════════════════
# SHARED STATE DEFINITION
# ══════════════════════════════════════════════════════════════════════
# This TypedDict defines the shape of the state object shared by all nodes.
# Each node reads what it needs and writes its results back to this state.
# Annotated[list, operator.add] tells LangGraph to MERGE lists when
# parallel nodes both write to the same key (instead of overwriting).

class AdvisorState(TypedDict):
    """The shared state that flows through all nodes in the pipeline."""
    raw_text: str                                       # Input: raw requirements.txt content
    packages: list                                      # Output of parse node
    pypi_results: Annotated[list, operator.add]         # Output of fetch node (merged)
    vuln_results: Annotated[list, operator.add]         # Output of vuln node (merged)
    scored_results: list                                # Output of score node
    final_report: list                                  # Output of narrate node
    # NEW: Stores the consolidated AI analysis of ALL packages together
    overall_summary: str                                # Output of narrate node (combined analysis)


# ══════════════════════════════════════════════════════════════════════
# NODE 1: PARSE — Extract packages from requirements.txt
# ══════════════════════════════════════════════════════════════════════

def parse_node(state: AdvisorState) -> dict:
    """
    Parse the raw requirements.txt text into structured package data.

    This node runs FIRST and alone. It reads the raw_text from state,
    parses it into a list of package dictionaries, and writes them back.
    """
    # Get the raw text from the shared state
    raw_text = state["raw_text"]

    # Use our parser to extract package info (name, version, pin_type)
    packages = parse_requirements(raw_text)

    # Write the parsed packages back to the shared state
    return {"packages": packages}


# ══════════════════════════════════════════════════════════════════════
# NODE 2a: FETCH — Get latest version from PyPI (runs in PARALLEL)
# ══════════════════════════════════════════════════════════════════════

def fetch_node(state: AdvisorState) -> dict:
    """
    Fetch PyPI data for every package in the list.

    This node runs IN PARALLEL with the vuln_node. Both read from
    state["packages"] at the same time, which speeds up the pipeline
    significantly (no need to wait for vulnerability checks to finish
    before starting PyPI fetches, or vice versa).
    """
    packages = state["packages"]
    results = []

    for pkg in packages:
        # Call the PyPI API for each package
        pypi_data = tool_fetch_pypi(pkg["name"])

        # Store the result with the package name so we can match it later
        results.append({
            "name": pkg["name"],
            "pypi_data": pypi_data
        })

    # Write results to shared state — Annotated[list, operator.add] merges them
    return {"pypi_results": results}


# ══════════════════════════════════════════════════════════════════════
# NODE 2b: VULN — Check vulnerabilities on OSV.dev (runs in PARALLEL)
# ══════════════════════════════════════════════════════════════════════

def vuln_node(state: AdvisorState) -> dict:
    """
    Check OSV.dev for vulnerabilities in each package.

    This node runs IN PARALLEL with fetch_node. It checks each package
    that has a known version against the OSV.dev vulnerability database.
    """
    packages = state["packages"]
    results = []

    for pkg in packages:
        if pkg["version"]:
            # Only check vulnerabilities if we know the current version
            vuln_data = tool_check_vulnerabilities(pkg["name"], pkg["version"])
        else:
            # Unpinned packages have no specific version to check
            vuln_data = {"cves": [], "error": "No version specified to check"}

        results.append({
            "name": pkg["name"],
            "vuln_data": vuln_data
        })

    # Write results to shared state
    return {"vuln_results": results}


# ══════════════════════════════════════════════════════════════════════
# NODE 3: SCORE — Analyze versions and calculate risk
# ══════════════════════════════════════════════════════════════════════

def score_node(state: AdvisorState) -> dict:
    """
    Score each package's risk level based on version gap and vulnerabilities.

    This node runs AFTER both fetch_node and vuln_node complete. It
    combines data from both parallel nodes and uses the scorer to
    calculate risk levels. The scorer is DETERMINISTIC — no LLM involved.

    NEW: Also enriches each package with EOL status, activity status,
    upgrade deadline, and minimum safe version information.
    """
    packages = state["packages"]
    pypi_results = state["pypi_results"]
    vuln_results = state["vuln_results"]

    # Build lookup dictionaries so we can quickly find data by package name
    # This is faster than searching through the list for each package
    pypi_lookup = {r["name"]: r["pypi_data"] for r in pypi_results}
    vuln_lookup = {r["name"]: r["vuln_data"] for r in vuln_results}

    # NEW: Get the current Python version ONCE at the top so we don't
    # call sys.version_info repeatedly for every package in the loop
    python_version = get_python_version()

    scored = []
    for pkg in packages:
        name = pkg["name"]

        # Get the PyPI data for this package (or empty defaults)
        pypi_data = pypi_lookup.get(name, {})
        latest_version = pypi_data.get("latest_version")
        all_versions = pypi_data.get("all_versions", [])
        last_updated = pypi_data.get("last_updated")
        pypi_error = pypi_data.get("error")

        # Get the vulnerability data for this package (or empty defaults)
        vuln_data = vuln_lookup.get(name, {})
        cves = vuln_data.get("cves", [])
        vuln_error = vuln_data.get("error")

        # Run the scoring algorithm — this is pure logic, no LLM
        score_result = analyze_and_score(
            current_version=pkg["version"],
            latest_version=latest_version,
            cves=cves,
            pin_type=pkg["pin_type"],
            last_updated=last_updated,
            all_versions=all_versions
        )

        # ── NEW: Enrich with EOL status from endoflife.date API ──
        # This checks if the package has reached or is approaching end-of-life
        eol_info = check_eol_status(name)

        # ── NEW: Check maintenance activity based on PyPI update history ──
        # This tells us if the package is actively maintained or possibly abandoned
        activity = check_last_activity(last_updated, all_versions)

        # ── NEW: Calculate a concrete upgrade deadline based on all risk factors ──
        # Combines EOL info, risk level, and CVE data into a single deadline
        upgrade_deadline = get_upgrade_deadline(
            eol_info=eol_info,
            risk_level=score_result["risk_level"],
            cves=cves
        )

        # ── NEW: Find the minimum safe version that fixes CVEs ──
        # This is the smallest upgrade needed, not necessarily the latest version
        min_safe = find_minimum_safe_version(
            package_name=name,
            current_version=pkg["version"],
            all_versions=all_versions,
            cves=cves,
            current_python=python_version
        )

        # Combine all data into a single result dictionary for this package
        scored.append({
            "name": name,
            "current_version": pkg["version"],
            "latest_version": latest_version,
            "pin_type": pkg["pin_type"],
            "cves": cves,
            "upgrade_type": score_result["upgrade_type"],
            "risk_score": score_result["risk_score"],
            "risk_level": score_result["risk_level"],
            "confidence_level": score_result["confidence_level"],
            "errors": [e for e in [pypi_error, vuln_error] if e],  # Collect any errors
            # NEW: Additional enrichment data from EOL checker and scorer
            "eol_info": eol_info,                   # Full EOL status dictionary
            "activity_status": activity,             # Maintenance activity dictionary
            "upgrade_deadline": upgrade_deadline,    # Deadline with urgency level
            "minimum_safe_version": min_safe,        # Earliest safe version or None
        })

    return {"scored_results": scored}


# ══════════════════════════════════════════════════════════════════════
# NODE 4: NARRATE — Gemini generates human-readable recommendations
# ══════════════════════════════════════════════════════════════════════

def narrate_node(state: AdvisorState) -> dict:
    """
    Use Gemini to generate human-readable recommendations for each package,
    PLUS a single consolidated analysis of all packages together.

    This node runs LAST, after all analysis is complete. Gemini acts as a
    NARRATOR only — it never decides risk levels or versions. All decisions
    were already made by the scorer. Gemini just explains them in plain English.

    NEW: After the per-package loop, a single Gemini call analyzes ALL packages
    together to provide an overall risk assessment, prioritized upgrade sequence,
    interaction risks, and concrete next steps.

    This uses "grounded generation": we feed Gemini only verified facts
    and tell it not to invent anything. This prevents hallucination.
    """
    scored_results = state["scored_results"]

    # Get the Gemini API key from environment variables — never hardcode secrets!
    api_key = os.environ.get("GEMINI_API_KEY")

    # Initialize the Gemini client using the google-genai SDK
    client = genai.Client(api_key=api_key)

    final_report = []

    for pkg in scored_results:
        # ── Generate the main recommendation ──
        # Fill in the prompt template with real, pre-computed facts
        rec_prompt = RECOMMENDATION_PROMPT.format(
            package_name=pkg["name"],
            current_version=pkg["current_version"] or "Not specified",
            latest_version=pkg["latest_version"] or "Unknown",
            upgrade_type=pkg["upgrade_type"],
            risk_level=pkg["risk_level"],
            risk_score=pkg["risk_score"],
            cves=", ".join(pkg["cves"]) if pkg["cves"] else "None found",
            pin_type=pkg["pin_type"],
            confidence_level=pkg["confidence_level"]
        )

        try:
            # Call Gemini to generate the recommendation text
            rec_response = client.models.generate_content(
                model="gemini-2.0-flash",  # Fast, capable model for text generation
                contents=rec_prompt
            )
            recommendation = rec_response.text
        except Exception as e:
            # If Gemini fails, provide a fallback message instead of crashing
            recommendation = (
                f"Could not generate recommendation: {str(e)}. "
                f"Risk level is {pkg['risk_level']} with {len(pkg['cves'])} CVE(s) found."
            )

        # ── Generate "what breaks" explanation for HIGH-RISK packages only ──
        what_breaks = None
        if pkg["risk_level"] == "High":
            wb_prompt = WHAT_BREAKS_PROMPT.format(
                package_name=pkg["name"],
                current_version=pkg["current_version"] or "Not specified",
                latest_version=pkg["latest_version"] or "Unknown",
                upgrade_type=pkg["upgrade_type"],
                cves=", ".join(pkg["cves"]) if pkg["cves"] else "None found"
            )

            try:
                wb_response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=wb_prompt
                )
                what_breaks = wb_response.text
            except Exception as e:
                what_breaks = f"Could not generate breaking changes analysis: {str(e)}"

        # Build the final report entry for this package
        final_report.append({
            "name": pkg["name"],
            "current_version": pkg["current_version"],
            "latest_version": pkg["latest_version"],
            "upgrade_type": pkg["upgrade_type"],
            "risk_level": pkg["risk_level"],
            "risk_score": pkg["risk_score"],
            "confidence_level": pkg["confidence_level"],
            "cves_found": pkg["cves"],
            "recommendation": recommendation,
            "what_breaks": what_breaks,  # None unless risk is High
            "errors": pkg["errors"],
            # NEW: Pass through the enrichment data from score_node to the frontend
            "eol_info": pkg.get("eol_info"),
            "activity_status": pkg.get("activity_status"),
            "upgrade_deadline": pkg.get("upgrade_deadline"),
            "minimum_safe_version": pkg.get("minimum_safe_version"),
        })

    # ── NEW: Single consolidated Gemini call for ALL packages together ──
    # Instead of analyzing each package in isolation, we build one big prompt
    # that includes all packages' facts and ask Gemini for a holistic analysis.
    overall_summary = ""

    try:
        # Build the combined facts string — one block per package
        all_facts_parts = []
        for pkg in scored_results:
            # Format each package's key facts into a readable block
            eol_msg = pkg.get("eol_info", {}).get("message", "Not checked")
            deadline_info = pkg.get("upgrade_deadline", {})
            deadline_str = deadline_info.get("deadline", "Not calculated")

            fact_block = (
                f"- Package: {pkg['name']}\n"
                f"  Current version: {pkg['current_version'] or 'Not specified'}\n"
                f"  Latest version: {pkg['latest_version'] or 'Unknown'}\n"
                f"  Upgrade type: {pkg['upgrade_type']}\n"
                f"  Risk level: {pkg['risk_level']} (score: {pkg['risk_score']})\n"
                f"  CVEs: {', '.join(pkg['cves']) if pkg['cves'] else 'None found'}\n"
                f"  EOL status: {eol_msg}\n"
                f"  Upgrade deadline: {deadline_str}\n"
            )
            all_facts_parts.append(fact_block)

        # Join all package fact blocks with blank lines for readability
        all_packages_facts = "\n".join(all_facts_parts)

        # Fill in the combined analysis prompt template
        combined_prompt = COMBINED_ANALYSIS_PROMPT.format(
            all_packages_facts=all_packages_facts
        )

        # Make a single Gemini call for the holistic analysis
        combined_response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=combined_prompt
        )
        overall_summary = combined_response.text

    except Exception as e:
        # If the combined analysis fails, don't crash — just note the failure
        overall_summary = f"Could not generate overall analysis: {str(e)}"

    return {
        "final_report": final_report,
        # NEW: Store the consolidated analysis in state for the API response
        "overall_summary": overall_summary
    }


# ══════════════════════════════════════════════════════════════════════
# BUILD THE LANGGRAPH WORKFLOW
# ══════════════════════════════════════════════════════════════════════

def build_graph():
    """
    Build and compile the LangGraph workflow.

    The graph looks like this:

        START → parse → fetch_pypi ──→ score → narrate → END
                     ↘ check_vulns ──↗

    The parse node runs first. Then fetch_pypi and check_vulns run IN PARALLEL.
    After both finish, score runs. Finally, narrate runs to generate text.

    Returns:
        A compiled LangGraph that can be invoked with initial state.
    """
    # Create a new state graph with our shared state schema
    builder = StateGraph(AdvisorState)

    # Register all our node functions
    builder.add_node("parse", parse_node)
    builder.add_node("fetch_pypi", fetch_node)
    builder.add_node("check_vulns", vuln_node)
    builder.add_node("score", score_node)
    builder.add_node("narrate", narrate_node)

    # Define the execution order with edges

    # START → parse: The parser runs first
    builder.add_edge(START, "parse")

    # parse → fetch_pypi AND parse → check_vulns: These two run IN PARALLEL
    # When a node has two outgoing edges, LangGraph executes both targets
    # at the same time. This is the key advantage of LangGraph!
    builder.add_edge("parse", "fetch_pypi")
    builder.add_edge("parse", "check_vulns")

    # fetch_pypi → score AND check_vulns → score: Score waits for BOTH
    # When a node has two incoming edges, it waits for all predecessors
    # to finish before running. This is called "fan-in."
    builder.add_edge("fetch_pypi", "score")
    builder.add_edge("check_vulns", "score")

    # score → narrate: Gemini narration runs after scoring
    builder.add_edge("score", "narrate")

    # narrate → END: Pipeline is complete
    builder.add_edge("narrate", END)

    # Compile the graph — this validates the edges and returns a runnable object
    return builder.compile()


def run_analysis(raw_text: str) -> dict:
    """
    Run the full dependency analysis pipeline on requirements.txt content.

    This is the main entry point called by the FastAPI endpoint.
    It builds the graph, feeds in the raw text, and returns the final report.

    Args:
        raw_text: The full contents of a requirements.txt file.

    Returns:
        A dictionary with "final_report" (list of package results) and
        "overall_summary" (consolidated AI analysis of all packages).
    """
    # Build a fresh graph instance
    graph = build_graph()

    # Invoke the graph with the initial state
    # The raw_text gets passed in, and the graph populates everything else
    result = graph.invoke({
        "raw_text": raw_text,
        "packages": [],
        "pypi_results": [],      # Empty list — will be populated by fetch_node
        "vuln_results": [],      # Empty list — will be populated by vuln_node
        "scored_results": [],
        "final_report": [],
        "overall_summary": ""    # NEW: Will be populated by narrate_node
    })

    # NEW: Return a dictionary with both the final report and overall summary
    # Previously this returned just result["final_report"] (a list)
    return {
        "final_report": result["final_report"],
        "overall_summary": result.get("overall_summary", "")
    }
