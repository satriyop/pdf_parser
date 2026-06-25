import re
import time

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _extract_spreadsheet_id(input_str):
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", input_str)
    if m:
        return m.group(1)
    if re.match(r"^[a-zA-Z0-9_-]{10,}$", input_str):
        return input_str
    return None


SA_EMAIL = "pdf-parser-sa@nex-project-500312.iam.gserviceaccount.com"


def _execute_with_retry(request, max_attempts=3, base_delay=4):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return request.execute()
        except (TimeoutError, ConnectionError, OSError) as e:
            last_error = e
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                print(f"  Retry API {attempt}/{max_attempts} after {delay}s: {e}")
                time.sleep(delay)
        except HttpError as e:
            status = e.resp.status if hasattr(e, "resp") else 0
            if status >= 500:
                last_error = e
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    print(f"  Retry API {attempt}/{max_attempts} after {delay}s (HTTP {status})")
                    time.sleep(delay)
            else:
                raise
    raise last_error


class SheetsWriter:
    def __init__(self, credentials_path, spreadsheet_url):
        self.creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )
        self.service = build("sheets", "v4", credentials=self.creds)

        sid = _extract_spreadsheet_id(spreadsheet_url)
        if not sid:
            raise ValueError(
                f"Could not extract spreadsheet ID from: {spreadsheet_url}\n"
                "Use the full URL: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID"
            )
        self.spreadsheet_id = sid
        self._initialized = set()

    def _close_http(self):
        if hasattr(self.service, "_http") and self.service._http:
            try:
                for conn in self.service._http.connections.values():
                    try:
                        conn.close()
                    except Exception:
                        pass
                self.service._http.connections.clear()
            except Exception:
                pass

    def _raise_on_api_error(self, e):
        status = e.resp.status if hasattr(e, "resp") else 0
        if status == 403:
            raise RuntimeError(
                f"Access denied. Share the sheet with {SA_EMAIL} as Editor."
            )
        if status == 404:
            raise RuntimeError("Spreadsheet not found. Check the URL.")
        if status == 429:
            raise RuntimeError("API quota exceeded. Try again later.")

    def _ensure_sheet(self, sheet_name):
        try:
            resp = _execute_with_retry(
                self.service.spreadsheets().get(
                    spreadsheetId=self.spreadsheet_id,
                    fields="sheets.properties",
                )
            )
            sheets = resp.get("sheets", [])
        except HttpError as e:
            self._raise_on_api_error(e)
            raise

        for s in sheets:
            if s["properties"]["title"] == sheet_name:
                return False

        body = {
            "requests": [{"addSheet": {"properties": {"title": sheet_name}}}]
        }
        try:
            _execute_with_retry(
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id, body=body
                )
            )
        except HttpError as e:
            raise RuntimeError(f"Failed to create sheet tab: {e}")
        return True

    def _init_sheet(self, sheet_name, headers):
        if sheet_name in self._initialized:
            return
        is_new = self._ensure_sheet(sheet_name)
        if is_new:
            range_name = f"'{sheet_name}'!A1"
            try:
                _execute_with_retry(
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=range_name,
                        valueInputOption="USER_ENTERED",
                        body={"values": [headers]},
                    )
                )
            except HttpError as e:
                self._raise_on_api_error(e)
                raise
            finally:
                self._close_http()
                time.sleep(0.5)
        self._initialized.add(sheet_name)

    def append_one(self, site, sheet_name="Survey Data"):
        headers = site.csv_headers()
        self._init_sheet(sheet_name, headers)
        row = site.to_xlsx_row()
        range_name = f"'{sheet_name}'!A1"
        try:
            _execute_with_retry(
                self.service.spreadsheets().values().append(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption="USER_ENTERED",
                    insertDataOption="INSERT_ROWS",
                    body={"values": [row]},
                )
            )
        except HttpError as e:
            self._raise_on_api_error(e)
            raise
        finally:
            self._close_http()
            time.sleep(0.3)

    def write(self, site_data_list, sheet_name="Survey Data"):
        if not site_data_list:
            return

        is_new_sheet = self._ensure_sheet(sheet_name)

        headers = site_data_list[0].csv_headers()
        rows = [headers]
        for site in site_data_list:
            rows.append(site.to_xlsx_row())

        range_name = f"'{sheet_name}'!A1"

        try:
            if is_new_sheet:
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption="USER_ENTERED",
                    body={"values": rows},
                ).execute()
            else:
                self.service.spreadsheets().values().append(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption="USER_ENTERED",
                    insertDataOption="INSERT_ROWS",
                    body={"values": rows},
                ).execute()
        except HttpError as e:
            status = e.resp.status if hasattr(e, "resp") else 0
            if status == 403:
                raise RuntimeError(
                    f"Access denied. Share the sheet with {SA_EMAIL} as Editor."
                )
            if status == 429:
                raise RuntimeError("API quota exceeded. Try again later.")
            raise

        url = f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"
        print(f"    Sheet URL: {url}")
