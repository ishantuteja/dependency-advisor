// ReportCard.jsx — Individual Package Analysis Card
//
// This component displays the analysis results for a single package.
// It shows: package name, versions, upgrade type badge, risk level badge,
// CVEs found, Gemini recommendation, and (for High risk) a collapsible
// "what breaks" explanation.
//
// NEW: Also displays upgrade_deadline (urgency badge), minimum_safe_version
// (blue info box), and activity_status (gray text below package name).

import React, { useState } from "react";

/**
 * Helper function to get the badge color class for upgrade types.
 * - patch = green (safe to upgrade)
 * - minor = yellow (moderate caution)
 * - major = red (breaking changes likely)
 */
function getUpgradeBadgeStyle(upgradeType) {
  switch (upgradeType) {
    case "patch":
      return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
    case "minor":
      return "bg-yellow-500/15 text-yellow-400 border-yellow-500/30";
    case "major":
      return "bg-red-500/15 text-red-400 border-red-500/30";
    case "up-to-date":
      return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
    default:
      return "bg-gray-500/15 text-gray-400 border-gray-500/30";
  }
}

/**
 * Helper function to get the badge color class for risk levels.
 */
function getRiskBadgeStyle(riskLevel) {
  switch (riskLevel) {
    case "High":
      return "bg-red-500/15 text-red-400 border-red-500/30";
    case "Medium":
      return "bg-yellow-500/15 text-yellow-400 border-yellow-500/30";
    case "Low":
      return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
    default:
      return "bg-gray-500/15 text-gray-400 border-gray-500/30";
  }
}

/**
 * Helper to get the left border accent color based on risk level.
 * This creates a visual hierarchy — high risk cards catch your eye first.
 */
function getRiskBorderColor(riskLevel) {
  switch (riskLevel) {
    case "High":
      return "border-l-red-500";
    case "Medium":
      return "border-l-yellow-500";
    case "Low":
      return "border-l-emerald-500";
    default:
      return "border-l-gray-500";
  }
}

/**
 * NEW: Helper function to get the badge color class for upgrade deadline urgency.
 * Maps urgency levels to colored badge styles:
 * - Critical = red (immediate action required)
 * - High = orange (action needed very soon)
 * - Medium = yellow (plan to address soon)
 * - Low = green (address at convenience)
 */
function getUrgencyBadgeStyle(urgency) {
  switch (urgency) {
    case "Critical":
      return "bg-red-500/15 text-red-400 border-red-500/30";
    case "High":
      return "bg-orange-500/15 text-orange-400 border-orange-500/30";
    case "Medium":
      return "bg-yellow-500/15 text-yellow-400 border-yellow-500/30";
    case "Low":
      return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
    default:
      return "bg-gray-500/15 text-gray-400 border-gray-500/30";
  }
}

/**
 * ReportCard component — displays analysis results for one package.
 *
 * Props:
 *   pkg    — the package result object from the backend
 *   index  — the position in the list (used for staggered animation delay)
 */
function ReportCard({ pkg, index }) {
  // State for the collapsible "what breaks" section (only for High risk)
  const [expanded, setExpanded] = useState(false);

  // Calculate animation delay based on position (caps at 0.5s for performance)
  const animDelay = Math.min(index * 0.05, 0.5);

  return (
    <div
      className={`glass rounded-xl border-l-4 ${getRiskBorderColor(pkg.risk_level)} opacity-0 animate-fade-in-up`}
      style={{ animationDelay: `${animDelay}s` }}
    >
      <div className="p-6">
        {/* ── Top Row: Package name, version info, and badges ── */}
        <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
          {/* Package name and version details */}
          <div>
            <h3 className="text-lg font-bold text-white">{pkg.name}</h3>

            {/* NEW: Show activity_status below the package name in gray text */}
            {/* This tells the user if the package is actively maintained or abandoned */}
            {pkg.activity_status && pkg.activity_status.activity_status && (
              <p className="text-xs text-gray-500 mt-0.5">
                {pkg.activity_status.activity_status}
                {/* Show days since update if available, for extra context */}
                {pkg.activity_status.days_since_last_update !== null && (
                  <span className="text-gray-600"> · updated {pkg.activity_status.days_since_last_update} days ago</span>
                )}
              </p>
            )}

            <div className="flex items-center gap-3 mt-1.5 text-sm">
              {/* Current version */}
              <span className="text-gray-500">
                Current: <span className="text-gray-300 font-mono">{pkg.current_version || "unpinned"}</span>
              </span>
              {/* Arrow separator */}
              <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
              {/* Latest version */}
              <span className="text-gray-500">
                Latest: <span className="text-gray-300 font-mono">{pkg.latest_version || "unknown"}</span>
              </span>
            </div>
          </div>

          {/* Badges container */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Upgrade type badge (patch/minor/major) */}
            <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getUpgradeBadgeStyle(pkg.upgrade_type)}`}>
              {pkg.upgrade_type === "up-to-date" ? "✓ Up to date" : pkg.upgrade_type}
            </span>
            {/* Risk level badge */}
            <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getRiskBadgeStyle(pkg.risk_level)}`}>
              {pkg.risk_level} Risk
            </span>
            {/* Confidence level badge */}
            <span className="px-3 py-1 rounded-full text-xs font-medium border bg-white/5 text-gray-400 border-white/10">
              {pkg.confidence_level} Confidence
            </span>

            {/* NEW: Upgrade deadline urgency badge */}
            {/* Shows a colored badge indicating how urgently this package should be upgraded */}
            {pkg.upgrade_deadline && pkg.upgrade_deadline.urgency && (
              <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getUrgencyBadgeStyle(pkg.upgrade_deadline.urgency)}`}>
                ⏰ {pkg.upgrade_deadline.deadline}
              </span>
            )}
          </div>
        </div>

        {/* NEW: Upgrade Deadline details — shows the deadline date and reason */}
        {/* Only renders if the backend provided upgrade deadline data */}
        {pkg.upgrade_deadline && pkg.upgrade_deadline.deadline_date && (
          <div className="mb-4 p-3 rounded-lg bg-white/5 border border-white/10">
            <p className="text-xs text-gray-400">
              <span className="font-semibold text-gray-300">Upgrade by:</span>{" "}
              <span className="font-mono">{pkg.upgrade_deadline.deadline_date}</span>
              {/* Show the reason for the deadline so the developer understands why */}
              {pkg.upgrade_deadline.reason && (
                <span className="text-gray-500"> — {pkg.upgrade_deadline.reason}</span>
              )}
            </p>
          </div>
        )}

        {/* NEW: Minimum Safe Version info box */}
        {/* Only shown when a minimum safe version exists (i.e., CVEs were found) */}
        {/* This shows the smallest upgrade needed to fix vulnerabilities */}
        {pkg.minimum_safe_version && (
          <div className="mb-4 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <p className="text-xs text-blue-400 flex items-center gap-1.5">
              {/* Info icon */}
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-semibold">Minimum safe version:</span>{" "}
              <span className="font-mono">{pkg.minimum_safe_version}</span>
            </p>
          </div>
        )}

        {/* ── CVEs Section ── */}
        {/* Only shows if vulnerabilities were found */}
        {pkg.cves_found && pkg.cves_found.length > 0 && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/5 border border-red-500/20">
            <p className="text-xs font-semibold text-red-400 mb-2 flex items-center gap-1.5">
              {/* Warning icon */}
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              Vulnerabilities Found
            </p>
            {/* List each CVE ID as a clickable pill */}
            <div className="flex flex-wrap gap-2">
              {pkg.cves_found.map((cve) => (
                <span key={cve} className="px-2 py-0.5 rounded bg-red-500/15 text-red-300 text-xs font-mono">
                  {cve}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* ── Gemini Recommendation ── */}
        {/* The AI-generated upgrade recommendation text */}
        {pkg.recommendation && (
          <div className="mb-4 p-4 rounded-lg bg-accent-500/5 border border-accent-500/15">
            <p className="text-xs font-semibold text-accent-400 mb-2 flex items-center gap-1.5">
              {/* Sparkle icon — represents AI-generated content */}
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
              </svg>
              AI Recommendation
            </p>
            <p className="text-sm text-gray-300 leading-relaxed">{pkg.recommendation}</p>
          </div>
        )}

        {/* ── "What Breaks" Collapsible Section ── */}
        {/* Only renders for High-risk packages that have a what_breaks analysis */}
        {pkg.what_breaks && (
          <div className="border-t border-white/5 pt-3">
            <button
              id={`what-breaks-${pkg.name}`}
              onClick={() => setExpanded(!expanded)}
              className="w-full flex items-center justify-between text-sm text-yellow-400/80 hover:text-yellow-300 transition-colors duration-200"
            >
              <span className="flex items-center gap-1.5 font-medium">
                {/* Lightning bolt icon — represents potential breakage */}
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                What could break if I upgrade?
              </span>
              {/* Chevron arrow that rotates when expanded */}
              <svg
                className={`w-4 h-4 transition-transform duration-300 ${expanded ? "rotate-180" : ""}`}
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Collapsible content — only visible when expanded is true */}
            {expanded && (
              <div className="mt-3 p-4 rounded-lg bg-yellow-500/5 border border-yellow-500/15 animate-fade-in-up">
                <p className="text-sm text-gray-300 leading-relaxed">{pkg.what_breaks}</p>
              </div>
            )}
          </div>
        )}

        {/* ── Errors Section ── */}
        {/* Shows any errors that occurred during analysis (API timeouts, etc.) */}
        {pkg.errors && pkg.errors.length > 0 && (
          <div className="mt-3 p-2 rounded-lg bg-orange-500/5 border border-orange-500/15">
            <p className="text-xs text-orange-400">
              ⚠ {pkg.errors.join(" | ")}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default ReportCard;
