"""
prompt.py — Gemini Prompt Templates (Grounded Generation)

This module stores all prompt templates used when calling the Gemini LLM.

We use a technique called "grounded generation": we give Gemini ONLY
pre-computed facts and explicitly tell it NOT to invent any information.

Why this matters:
LLMs can "hallucinate" — they might make up version numbers like "4.2.99"
or fake CVE IDs like "CVE-2024-99999" that don't exist. By feeding in only
verified facts and instructing the model to use ONLY those facts, we prevent
this dangerous behavior.
"""

# ── Prompt for generating the upgrade recommendation ──
# Used for EVERY package to produce a human-readable recommendation.
# All the {placeholders} get filled in with real data from our analyzer.
RECOMMENDATION_PROMPT = """You are a dependency upgrade advisor helping a Python developer.

CRITICAL RULES — YOU MUST FOLLOW THESE:
1. You must ONLY use the facts provided below. Do NOT invent or guess any version numbers, CVE IDs, package names, or any other information.
2. If a fact is missing or says "None", say "information not available" instead of guessing.
3. Keep your response to 2-3 concise, actionable sentences.
4. Tell the developer specifically what to do (upgrade, pin, monitor, etc.).
5. Do NOT add any CVE IDs or version numbers that are not in the facts below.

VERIFIED FACTS (from our automated analysis):
- Package name: {package_name}
- Current version: {current_version}
- Latest version: {latest_version}
- Upgrade type: {upgrade_type}
- Risk level: {risk_level}
- Risk score: {risk_score}
- CVEs found: {cves}
- Pin type: {pin_type}
- Confidence level: {confidence_level}

Based ONLY on the facts above, write a concise upgrade recommendation."""


# ── Prompt for explaining "what breaks if I upgrade" ──
# Only used for HIGH-RISK packages where developers need extra guidance.
# This helps developers understand the risk before upgrading.
WHAT_BREAKS_PROMPT = """You are a dependency upgrade advisor explaining potential breaking changes.

CRITICAL RULES — YOU MUST FOLLOW THESE:
1. You must ONLY use the facts provided below. Do NOT invent breaking changes, API names, or migration steps that are not supported by the facts.
2. Speak in general terms about what TYPICALLY breaks in this type of upgrade.
3. Keep your response to 3-4 concise sentences.
4. Recommend the developer check the package's changelog before upgrading.

VERIFIED FACTS (from our automated analysis):
- Package name: {package_name}
- Current version: {current_version}
- Latest version: {latest_version}
- Upgrade type: {upgrade_type}
- CVEs found: {cves}

Based ONLY on the facts above, explain what could potentially break if the developer upgrades this package. Be honest about uncertainty — say "check the changelog" rather than inventing specific breaking changes."""


# ── NEW: Prompt for consolidated analysis of ALL packages together ──
# Used once per scan to provide a holistic view of the entire dependency set.
# Instead of analyzing each package in isolation, this prompt asks Gemini to
# consider how all the dependencies interact and suggest an upgrade strategy.
COMBINED_ANALYSIS_PROMPT = """You are a senior Python dependency advisor analyzing a project's ENTIRE dependency set.

CRITICAL RULES — YOU MUST FOLLOW THESE:
1. You must ONLY use the facts provided below. Do NOT invent or guess any version numbers, CVE IDs, package names, or any other information.
2. If a fact is missing or says "None", say "information not available" instead of guessing.
3. Provide actionable, developer-friendly advice.
4. Do NOT add any CVE IDs, version numbers, or package names that are not in the facts below.

VERIFIED FACTS FOR ALL PACKAGES:
{all_packages_facts}

Based ONLY on the facts above, provide:

1. **Overall Risk Assessment**: A 2-3 sentence summary of the health of this dependency set. How critical is the situation overall?

2. **Prioritized Upgrade Sequence**: List the packages in the exact order they should be upgraded (most urgent first). For each, give a one-line reason why it has that priority.

3. **Interaction Risks**: Are there any packages in this set that commonly depend on each other? If upgrading one might require upgrading another, mention it. If you are unsure, say so honestly rather than guessing.

4. **Concrete Next Steps**: Give 3-5 specific, actionable steps the developer should take right now. Be concise and practical."""

