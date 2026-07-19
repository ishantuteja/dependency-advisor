// App.jsx — Main Application Component
//
// This is the root component that holds the entire application.
// It manages the global state (scan results, loading status, errors)
// and renders the UploadBox and ReportCard components.

import React, { useState } from "react";     // useState hook for managing state
import UploadBox from "./components/UploadBox.jsx";   // File upload / paste component
import ReportCard from "./components/ReportCard.jsx"; // Individual package result card

// The URL where our FastAPI backend is running
const API_URL = "http://localhost:8000";

function App() {
  // ── State variables ──
  // results: the array of package analysis results from the backend
  const [results, setResults] = useState(null);
  // loading: true while we're waiting for the backend to respond
  const [loading, setLoading] = useState(false);
  // error: holds an error message string if something goes wrong
  const [error, setError] = useState(null);
  // totalPackages: count of packages scanned (from the API response)
  const [totalPackages, setTotalPackages] = useState(0);
  // NEW: overallSummary: the consolidated AI analysis of all packages together
  const [overallSummary, setOverallSummary] = useState(null);

  /**
   * Handle the scan button click — sends content to the backend for analysis.
   * This function is passed down to the UploadBox component as a prop.
   *
   * @param {string} content - The raw requirements.txt text to analyze.
   */
  const handleScan = async (content) => {
    // Reset previous results and errors before starting a new scan
    setLoading(true);
    setError(null);
    setResults(null);
    setTotalPackages(0);
    setOverallSummary(null);  // NEW: Reset the overall summary too

    try {
      // Send a POST request to the /analyze endpoint with the text content
      const response = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: content }),   // Send as JSON body
      });

      // If the backend returns an error status, extract the error message
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${response.status}`);
      }

      // Parse the successful JSON response
      const data = await response.json();

      // Update state with the results
      setTotalPackages(data.total_packages);
      setResults(data.results);
      // NEW: Store the consolidated AI analysis from the backend response
      setOverallSummary(data.overall_summary || null);
    } catch (err) {
      // Show a friendly error message instead of crashing the UI
      setError(err.message || "An unexpected error occurred. Is the backend running?");
    } finally {
      // Always stop the loading spinner, whether we succeeded or failed
      setLoading(false);
    }
  };

  // ── Helper function to count packages by risk level ──
  // Used for the summary bar at the top of results
  const countByRisk = (level) => {
    if (!results) return 0;
    return results.filter((r) => r.risk_level === level).length;
  };

  return (
    <div className="min-h-screen bg-surface-900">
      {/* ── Header ── */}
      <header className="border-b border-white/5">
        <div className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
          {/* Logo and title */}
          <div className="flex items-center gap-3">
            {/* Shield icon — represents security scanning */}
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-500 to-purple-600 flex items-center justify-center shadow-lg shadow-accent-500/25">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                Dependency Advisor
              </h1>
              <p className="text-xs text-gray-500">AI-powered upgrade recommendations</p>
            </div>
          </div>
          {/* Status indicator dot — shows the app is active */}
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            Online
          </div>
        </div>
      </header>

      {/* ── Main Content ── */}
      <main className="max-w-6xl mx-auto px-6 py-10">
        {/* Upload / Paste area */}
        <UploadBox onScan={handleScan} loading={loading} />

        {/* ── Error Message ── */}
        {/* Only shows if an error occurred — displays a friendly red banner */}
        {error && (
          <div className="mt-8 p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 flex items-start gap-3 animate-fade-in-up">
            {/* Warning icon */}
            <svg className="w-5 h-5 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <div>
              <p className="font-semibold">Analysis Failed</p>
              <p className="text-sm mt-1 text-red-400">{error}</p>
            </div>
          </div>
        )}

        {/* ── Loading State ── */}
        {/* Shows a spinner and animated text while the backend is working */}
        {loading && (
          <div className="mt-12 flex flex-col items-center gap-4 animate-fade-in-up">
            {/* Spinning circle loader */}
            <div className="w-12 h-12 border-4 border-accent-500/30 border-t-accent-400 rounded-full animate-spin"></div>
            <p className="text-gray-400 text-sm">Scanning dependencies and checking for vulnerabilities...</p>
            <p className="text-gray-600 text-xs">This may take a moment for large files</p>
          </div>
        )}

        {/* ── Results Section ── */}
        {/* Only renders when we have results and are not loading */}
        {results && !loading && (
          <div className="mt-10 animate-fade-in-up">

            {/* ── NEW: Overall AI Summary Card ── */}
            {/* Displays the consolidated Gemini analysis of ALL packages together */}
            {/* This appears at the very top of results so the developer sees the big picture first */}
            {overallSummary && (
              <div className="glass rounded-2xl p-6 mb-8 border border-accent-500/20">
                <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                  {/* Brain icon — represents holistic AI analysis */}
                  <svg className="w-5 h-5 text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  Overall Dependency Analysis
                </h2>
                <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-line">
                  {overallSummary}
                </div>
              </div>
            )}

            {/* ── Summary Bar ── */}
            {/* Shows at-a-glance stats: total scanned and breakdown by risk level */}
            <div className="glass rounded-2xl p-6 mb-8">
              <h2 className="text-lg font-semibold text-white mb-4">Scan Summary</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {/* Total packages scanned */}
                <div className="bg-white/5 rounded-xl p-4 text-center">
                  <p className="text-3xl font-bold text-white">{totalPackages}</p>
                  <p className="text-xs text-gray-400 mt-1">Total Scanned</p>
                </div>
                {/* High risk count — red */}
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-center">
                  <p className="text-3xl font-bold text-red-400">{countByRisk("High")}</p>
                  <p className="text-xs text-red-400/80 mt-1">High Risk</p>
                </div>
                {/* Medium risk count — yellow */}
                <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 text-center">
                  <p className="text-3xl font-bold text-yellow-400">{countByRisk("Medium")}</p>
                  <p className="text-xs text-yellow-400/80 mt-1">Medium Risk</p>
                </div>
                {/* Low risk count — green */}
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 text-center">
                  <p className="text-3xl font-bold text-emerald-400">{countByRisk("Low")}</p>
                  <p className="text-xs text-emerald-400/80 mt-1">Low Risk</p>
                </div>
              </div>
            </div>

            {/* ── Package Cards ── */}
            {/* Render a ReportCard for each analyzed package */}
            <div className="space-y-4">
              {results.map((pkg, index) => (
                <ReportCard key={pkg.name} pkg={pkg} index={index} />
              ))}
            </div>
          </div>
        )}
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-white/5 mt-16">
        <div className="max-w-6xl mx-auto px-6 py-6 text-center text-gray-600 text-sm">
          Dependency Upgrade Advisor — Powered by Gemini AI & OSV.dev
        </div>
      </footer>
    </div>
  );
}

export default App;
