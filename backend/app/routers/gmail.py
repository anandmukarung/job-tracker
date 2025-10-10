from fastapi import APIRouter, Request, HTTPException, Query
from ..services.gmail_client import (
    get_authorize_url,
    exchange_code_and_save_tokens,
    fetch_job_candidates_from_gmail,
    load_credentials,
)

router = APIRouter(prefix="/gmail", tags=["Gmail"])

# Generate authorization URL
@router.get("/auth/url")
def get_auth_url(request: Request):
    """
    Generates a Google OAuth URL for the user to grant Gmail access.
    """
    redirect_uri = str(request.url_for("gmail_callback"))
    try:
        url = get_authorize_url(redirect_uri)
        return {"auth_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Callback endpoint for OAuth
@router.get("/auth/callback", name="gmail_callback")
def gmail_callback(request: Request, code: str):
    """
    Handles OAuth callback after the user authorizes the app.
    Exchanges code for token and saves credentials.json.
    """
    redirect_uri = str(request.url_for("gmail_callback"))
    try:
        creds = exchange_code_and_save_tokens(code, redirect_uri)
        return {"message": "Authorization successful!", "credentials": creds}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth failed: {str(e)}")


# Check connection status
@router.get("/status")
def gmail_status():
    """
    Checks whether valid Gmail credentials are available.
    """
    creds = load_credentials()
    if creds is None:
        return {"authorized": False, "message": "No credentials found."}
    return {"authorized": True, "token_expired": not creds.valid}


# Fetch job candidates
@router.get("/jobs")
def get_jobs_from_gmail(
    query: str = Query(
        "applied OR 'thank you for your application' newer_than:365d",
        description="Gmail search query to filter job-related emails",
    ),
    max_results: int = Query(20, ge=1, le=200)
):
    """
    Fetch job application emails and parse possible job candidates.
    """
    try:
        jobs = fetch_job_candidates_from_gmail(query=query, max_results=max_results)
        return {"count": len(jobs), "jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Gmail jobs: {str(e)}")