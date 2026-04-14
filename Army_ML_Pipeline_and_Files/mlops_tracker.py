import os
import json
import time
from datetime import datetime

class MLOpsTracker:
    def __init__(self, experiment_name="VehicleHealth_V3"):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.logs_dir = os.path.join(self.base_dir, 'reports', 'mlops')
        os.makedirs(self.logs_dir, exist_ok=True)
        
        self.experiment_name = experiment_name
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_file = os.path.join(self.logs_dir, f"run_{self.run_id}.json")
        
        self.run_data = {
            "experiment": self.experiment_name,
            "run_id": self.run_id,
            "start_time": datetime.now().isoformat(),
            "metrics": {},
            "params": {},
            "artifacts": {}
        }

    def log_param(self, key, value):
        # Ensure JSON serializable
        if hasattr(value, 'item'): value = value.item()
        self.run_data["params"][key] = value
        self._save()

    def log_metric(self, key, value):
        # Ensure JSON serializable
        if hasattr(value, 'item'): value = float(value.item())
        else: value = float(value)
        
        if key not in self.run_data["metrics"]:
            self.run_data["metrics"][key] = []
        self.run_data["metrics"][key].append({
            "value": value,
            "timestamp": datetime.now().isoformat()
        })
        self._save()

    def log_artifact(self, name, path):
        self.run_data["artifacts"][name] = {
            "path": path,
            "size_kb": round(os.path.getsize(path) / 1024, 2) if os.path.exists(path) else 0
        }
        self._save()

    def finalize(self):
        self.run_data["end_time"] = datetime.now().isoformat()
        self.run_data["status"] = "SUCCESS"
        self._save()
        print(f"  [MLOps] Run {self.run_id} finalized and saved.")

    def _save(self):
        with open(self.run_file, 'w') as f:
            json.dump(self.run_data, f, indent=4)

def get_latest_run():
    # Helper to retrieve the most recent MLOps run for the dashboard
    import glob
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports', 'mlops')
    files = glob.glob(os.path.join(logs_dir, "run_*.json"))
    if not files: return None
    latest = max(files, key=os.path.getctime)
    with open(latest, 'r') as f:
        return json.load(f)
