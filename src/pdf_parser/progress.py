import json
import os


class ProgressTracker:
    def __init__(self, output_path):
        self.path = output_path + ".progress.json"
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                return json.load(f)
        return {"context": "", "processed": []}

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def is_done(self, file_id):
        return file_id in self.data["processed"]

    def mark_done(self, file_id):
        if file_id not in self.data["processed"]:
            self.data["processed"].append(file_id)
            self._save()

    def clear(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def done_count(self):
        return len(self.data["processed"])

    def remaining(self, selected_files):
        return [f for f in selected_files if not self.is_done(f["id"])]
