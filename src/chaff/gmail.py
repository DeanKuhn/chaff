"""Auth and code fetching for gmail API (needed for recovery email verification)."""

import base64
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from chaff.exceptions import GmailError

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = Path.home() / ".chaff" / "token.json"
CLIENT_SECRET_PATH = Path.home() / ".chaff" / "client_secret.json"

def get_gmail_service():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or creds.expired:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def fetch_verification_code(service) -> str:
    query = "subject:verification newer_than:2m"
    results = service.users().messages().list(userId="me", q=query, maxResults=1).execute()
    if "messages" not in results:
        raise GmailError("Failed to find verification code")
    
    msg_id = results["messages"][0]["id"]
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    payload = msg["payload"]
    if "parts" in payload:
        data = payload["parts"][0]["body"]["data"]
    else:
        data = payload["body"]["data"]

    body_text = base64.urlsafe_b64decode(data).decode("utf-8")
    match = re.search(r"\b\d{6}\b", body_text)
    if not match:
        raise GmailError("Could not parse verification code from email")

    return match.group()
