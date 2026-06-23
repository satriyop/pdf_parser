import re

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _extract_spreadsheet_id(input_str):
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", input_str)
    if m:
        return m.group(1)
    if re.match(r"^[a-zA-Z0-9_-]{10,}$", input_str):
        return input_str
    return None


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

    def _ensure_sheet(self, sheet_name):
        sheets = (
            self.service.spreadsheets()
            .get(
                spreadsheetId=self.spreadsheet_id,
                fields="sheets.properties",
            )
            .execute()
            .get("sheets", [])
        )

        for s in sheets:
            if s["properties"]["title"] == sheet_name:
                return False

        body = {
            "requests": [{"addSheet": {"properties": {"title": sheet_name}}}]
        }
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id, body=body
        ).execute()
        return True

    def write(self, site_data_list, sheet_name="Survey Data"):
        if not site_data_list:
            return

        is_new_sheet = self._ensure_sheet(sheet_name)

        headers = site_data_list[0].csv_headers()
        rows = [headers]
        for site in site_data_list:
            rows.append(site.to_xlsx_row())

        range_name = f"'{sheet_name}'!A1"

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

        url = f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"
        print(f"    Sheet URL: {url}")
