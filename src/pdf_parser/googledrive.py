import os
import sys

from google.auth.exceptions import DefaultCredentialsError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

_DRIVE_KWARGS = {
    "supportsAllDrives": True,
    "includeItemsFromAllDrives": True,
}


def get_credentials(credentials_path=None, scopes=None):
    if scopes is None:
        scopes = SCOPES
    if credentials_path:
        return service_account.Credentials.from_service_account_file(
            credentials_path, scopes=scopes
        )
    try:
        from google.auth import default as default_creds
        creds, _ = default_creds(scopes=scopes)
        return creds
    except DefaultCredentialsError:
        raise RuntimeError(
            "No credentials found. Provide --credentials or set "
            "GOOGLE_APPLICATION_CREDENTIALS env var."
        )


class DriveClient:
    def __init__(self, credentials_path=None):
        self.creds = get_credentials(credentials_path)
        self.service = build("drive", "v3", credentials=self.creds)

    def list_files(self, folder_id=None, search=None, page_size=100):
        files = []

        if folder_id:
            files = self._walk_folder(folder_id, search=search)
        else:
            query_parts = ["mimeType='application/pdf'"]
            if search:
                query_parts.append(f"name contains '{search}'")
            query = " and ".join(query_parts)

            page_token = None
            while True:
                resp = (
                    self.service.files()
                    .list(
                        q=query,
                        spaces="drive",
                        fields="nextPageToken, files(id, name, size)",
                        pageSize=page_size,
                        pageToken=page_token,
                        **_DRIVE_KWARGS,
                    )
                    .execute()
                )
                files.extend(resp.get("files", []))
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break

        return files

    def _walk_folder(self, folder_id, search=None):
        files = []
        page_token = None

        while True:
            resp = (
                self.service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType, size)",
                    pageSize=100,
                    pageToken=page_token,
                    **_DRIVE_KWARGS,
                )
                .execute()
            )

            for f in resp.get("files", []):
                if f["mimeType"] == "application/pdf":
                    if not search or search.lower() in f["name"].lower():
                        files.append({"id": f["id"], "name": f["name"], "size": f.get("size", 0)})
                elif "folder" in f["mimeType"]:
                    files.extend(self._walk_folder(f["id"], search=search))

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        return files

    def inspect_folder(self, folder_id, depth=0, max_depth=2):
        lines = []
        page_token = None
        while True:
            resp = (
                self.service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageSize=100,
                    pageToken=page_token,
                    **_DRIVE_KWARGS,
                )
                .execute()
            )
            for f in resp.get("files", []):
                is_folder = "folder" in f["mimeType"]
                prefix = "  " * (depth + 1) + ("[D]" if is_folder else "[F]")
                lines.append(f"{prefix} {f['name']}")
                if is_folder and depth < max_depth:
                    lines.extend(self.inspect_folder(f["id"], depth + 1, max_depth))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return lines

    def download(self, file_id, dest_path):
        request = self.service.files().get_media(fileId=file_id)
        with open(dest_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

    def pick_interactive(self, folder_id=None, search=None):
        files = self.list_files(folder_id=folder_id, search=search)
        if not files:
            print("No PDF files found.")
            return []

        files.sort(key=lambda f: f.get("name", ""))

        print(f"\nFound {len(files)} PDF(s):")
        for i, f in enumerate(files, 1):
            size_kb = int(f.get("size", 0)) / 1024
            print(f"  [{i}] {f['name']} ({size_kb:.0f} KB)")

        print("\nEnter numbers separated by space (e.g. '1 3 5'),")
        print("or 'all' to select all, or blank to cancel.")
        choice = input(">> ").strip()

        if not choice:
            return []
        if choice.lower() == "all":
            return files

        selected = []
        for part in choice.split():
            try:
                idx = int(part) - 1
                if 0 <= idx < len(files):
                    selected.append(files[idx])
            except ValueError:
                pass
        return selected

    def download_selected(self, selected_files, dest_dir):
        downloaded = []
        for f in selected_files:
            name = f["name"]
            dest = os.path.join(dest_dir, name)
            print(f"    Downloading {name} ...", end=" ", flush=True)
            try:
                self.download(f["id"], dest)
                downloaded.append(dest)
                print("OK")
            except Exception as e:
                print(f"FAILED: {e}")
        return downloaded
