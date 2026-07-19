// UploadBox.jsx — File Upload and Text Paste Component
//
// This component lets the user either:
//   1. Paste requirements.txt content directly into a textarea
//   2. Upload a .txt file from their computer
//
// It also has the "Scan" button that triggers the analysis.

import React, { useState, useRef } from "react";

/**
 * UploadBox component — the input area for requirements.txt content.
 *
 * Props:
 *   onScan(content)  — callback function called when the user clicks "Scan"
 *   loading           — boolean, true when a scan is in progress
 */
function UploadBox({ onScan, loading }) {
  // The text content in the textarea (controlled component)
  const [text, setText] = useState("");
  // Reference to the hidden file input element (so we can trigger it programmatically)
  const fileInputRef = useRef(null);

  /**
   * Handle file upload — reads the selected file and puts its content in the textarea.
   */
  const handleFileUpload = (e) => {
    const file = e.target.files[0];   // Get the first (and only) selected file

    if (!file) return;  // User cancelled the file picker

    // FileReader lets us read file contents in the browser
    const reader = new FileReader();

    // This callback fires when the file has been fully read
    reader.onload = (event) => {
      setText(event.target.result);  // Put the file contents into the textarea
    };

    // Start reading the file as text (UTF-8)
    reader.readAsText(file);
  };

  /**
   * Handle the Scan button click — validates input and calls the parent's onScan.
   */
  const handleScan = () => {
    // Don't allow scanning if the textarea is empty
    if (!text.trim()) return;
    // Call the parent component's scan handler with the textarea content
    onScan(text);
  };

  return (
    <div className="glass rounded-2xl p-8">
      {/* Section title and description */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          {/* Upload cloud icon */}
          <svg className="w-5 h-5 text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          Upload or Paste Requirements
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Paste your <code className="px-1.5 py-0.5 rounded bg-white/10 text-accent-400 text-xs">requirements.txt</code> content below or upload a file.
        </p>
      </div>

      {/* ── Textarea for pasting content ── */}
      <textarea
        id="requirements-input"
        className="w-full h-48 bg-surface-900/80 border border-white/10 rounded-xl p-4 text-sm text-gray-300 font-mono placeholder-gray-600 focus:outline-none focus:border-accent-500/50 focus:ring-2 focus:ring-accent-500/20 transition-all duration-300 resize-none"
        placeholder={`# Paste your requirements.txt here...\nflask==2.3.1\ndjango>=4.2\nrequests\nnumpy==1.24.0`}
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={loading}  // Disable while scanning to prevent edits
      />

      {/* ── Action Buttons ── */}
      <div className="flex items-center gap-3 mt-4">
        {/* Upload File button — triggers the hidden file input */}
        <button
          id="upload-file-btn"
          onClick={() => fileInputRef.current.click()}
          disabled={loading}
          className="px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-sm text-gray-400 hover:bg-white/10 hover:text-white transition-all duration-300 flex items-center gap-2 disabled:opacity-50"
        >
          {/* Folder icon */}
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
          Upload File
        </button>

        {/* Hidden file input — only accepts .txt files */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileUpload}
          accept=".txt"
          className="hidden"  // Visually hidden, triggered by the button above
        />

        {/* Clear button — resets the textarea */}
        <button
          id="clear-btn"
          onClick={() => setText("")}
          disabled={loading || !text}
          className="px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-sm text-gray-400 hover:bg-white/10 hover:text-white transition-all duration-300 disabled:opacity-50"
        >
          Clear
        </button>

        {/* Spacer — pushes the Scan button to the right */}
        <div className="flex-1"></div>

        {/* ── SCAN BUTTON ── */}
        {/* The main action button — glows to attract attention */}
        <button
          id="scan-btn"
          onClick={handleScan}
          disabled={loading || !text.trim()}
          className={`px-6 py-2.5 rounded-xl font-semibold text-sm transition-all duration-300 flex items-center gap-2 ${loading || !text.trim()
              ? "bg-accent-600/30 text-accent-400/50 cursor-not-allowed"
              : "bg-gradient-to-r from-accent-500 to-purple-600 text-white hover:from-accent-400 hover:to-purple-500 shadow-lg shadow-accent-500/25 pulse-glow"
            }`}
        >
          {/* Show spinner while loading, radar icon otherwise */}
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              Scanning...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Scan Dependencies
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export default UploadBox;
