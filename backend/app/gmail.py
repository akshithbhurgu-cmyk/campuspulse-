"""Local, user-authorized Gmail read-only access for Phase 11."""
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS = Path("credentials.json")
TOKEN = Path("gmail_token.json")


def authorize() -> None:
    creds = Credentials.from_authorized_user_file(TOKEN, SCOPES) if TOKEN.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS.exists():
                raise FileNotFoundError("credentials.json is missing from backend.")
            creds = InstalledAppFlow.from_client_secrets_file(CREDENTIALS, SCOPES).run_local_server(port=0)
        TOKEN.write_text(creds.to_json())


def status() -> bool:
    return TOKEN.exists()


def recent_messages(query: str = "", max_results: int = 10) -> list[dict[str, str]]:
    if not TOKEN.exists():
        raise RuntimeError("Gmail is not authorized yet.")
    creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    listed = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    result = []
    for ref in listed.get("messages", []):
        message = service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
        headers = {item["name"].lower(): item["value"] for item in message["payload"].get("headers", [])}
        def body(part):
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"] + "==").decode("utf-8", "replace")
            return "".join(body(child) for child in part.get("parts", []))
        text = body(message["payload"])
        if text:
            result.append({"id": message["id"], "text": f"Subject: {headers.get('subject', '')}\n\n{text}"})
    return result


if __name__ == "__main__":
    authorize()
    print("Gmail authorization completed.")
