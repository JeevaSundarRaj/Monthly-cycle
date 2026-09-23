from openpyxl import Workbook, load_workbook
from datetime import datetime
import os


class ExcelLogger:
    def __init__(self, file_path="call_logs.xlsx"):
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            self.wb = Workbook()
            self.ws = self.wb.active
            self.ws.append([
                "Timestamp", "PolicyType", "Option", "TeamType", "TeamName",
                "CallType", "CallID", "CallURL", "Status", "Remarks"
            ])
            self.wb.save(self.file_path)
        else:
            self.wb = load_workbook(self.file_path)
            self.ws = self.wb.active

    def log_call(self, policy_type, option, team_type, team_name, call_type, call_id, status, remarks):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        call_url = f"https://dialpadbeta.com/csr/call/{call_id}" if call_id else ""
        self.ws.append([
            timestamp, policy_type, option, team_type, team_name,
            call_type, call_id, call_url, status, remarks
        ])
        self.wb.save(self.file_path)
