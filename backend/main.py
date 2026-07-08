"""
main.py — FastAPI Application

This is the entry point for the backend server. It exposes two endpoints:

1. POST /analyze — Accepts a requirements.txt file upload, runs the full
   analysis pipeline, and returns a JSON report with upgrade recommendations.

2. GET /health — Simple health check that returns {"status": "ok"}.

The server uses CORS middleware so the React frontend can call the API
from a different port (Vite runs on :5173, FastAPI on :8000).
"""

import os  # For reading environment variables
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, UploadFile, File, HTTPException  # Web framework
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware  # Cross-Origin Resource Sharing
from pydantic import BaseModel  # For request body validation

from agent import run_analysis  # Our LangGraph pipeline


# ══════════════════════════════════════════════════════════════════════
# CREATE THE FASTAPI APP
# ══════════════════════════════════════════════════════════════════════

# Initialize the FastAPI application with metadata for the docs page
app = FastAPI(
    title="Dependency Upgrade Advisor",
    description="Scan Python requirements.txt files for outdated packages, "
                "vulnerabilities, and get AI-powered upgrade recommendations.",
    version="1.0.0"
)

# ── Configure CORS ──
# CORS (Cross-Origin Resource Sharing) allows the React frontend
# running on localhost:5173 to make requests to this API on localhost:8000.
# Without this, the browser would block the requests for security reasons.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Allow requests from any origin (for development)
    allow_credentials=True,
    allow_methods=["*"],       # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],       # Allow all headers
)


# ══════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ══════════════════════════════════════════════════════════════════════

class TextInput(BaseModel):
    """
    Request body for the /analyze endpoint when sending raw text.
    This is used when the frontend sends pasted text (not a file upload).
    """
    content: str  # The raw requirements.txt content as a string


# ══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@app.get("/health")
def health_check():
    """
    Health check endpoint — returns a simple status message.

    Used by monitoring tools and the frontend to verify the backend is running.
    Returns {"status": "ok"} if the server is alive.
    """
    return {"status": "ok"}


@app.post("/analyze")
async def analyze_dependencies(file: UploadFile = File(None), body: TextInput = None):
    """
    Main analysis endpoint — scans a requirements.txt and returns recommendations.

    Accepts EITHER:
    - A file upload (multipart/form-data with a .txt file)
    - A JSON body with {"content": "raw requirements.txt text"}

    Runs the full LangGraph pipeline:
    parse → fetch+vuln (parallel) → score → narrate

    Returns a JSON response with total_packages and a results array.
    """
    # ── Step 1: Get the requirements.txt content from the request ──
    raw_text = None

    if file:
        # File was uploaded — read its contents as a string
        try:
            contents = await file.read()
            raw_text = contents.decode("utf-8")  # Convert bytes to string
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Could not read uploaded file: {str(e)}"
            )
    elif body and body.content:
        # Raw text was sent in the JSON body
        raw_text = body.content
    else:
        # Neither file nor text was provided — return an error
        raise HTTPException(
            status_code=400,
            detail="Please provide either a file upload or text content."
        )

    # Validate that the content is not empty
    if not raw_text.strip():
        raise HTTPException(
            status_code=400,
            detail="The provided content is empty."
        )

    # ── Step 2: Check that the Gemini API key is configured ──
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY environment variable is not set. "
                   "Please set it before running the analysis."
        )

    # ── Step 3: Run the full analysis pipeline ──
    try:
        # NEW: run_analysis now returns a dict with "final_report" and "overall_summary"
        # Previously it returned just the list of package results
        analysis_result = run_analysis(raw_text)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis pipeline failed: {str(e)}"
        )

    # ── Step 4: Build and return the response ──
    # NEW: Extract the final_report list and overall_summary from the result dict
    report = analysis_result.get("final_report", [])
    overall_summary = analysis_result.get("overall_summary", "")

    return {
        "total_packages": len(report),
        "results": report,
        # NEW: Include the consolidated AI analysis of all packages together
        "overall_summary": overall_summary
    }


# ══════════════════════════════════════════════════════════════════════
# RUN THE SERVER
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn  # ASGI server for running FastAPI

    # Start the server on port 8000, accessible from any network interface
    # reload=True enables auto-restart when code changes (great for development)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
