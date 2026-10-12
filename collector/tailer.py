import os
import json
import time
import httpx
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("collector")

LOG_FILE = os.environ.get("LOG_FILE", os.path.join(os.path.dirname(__file__), "..", "logs", "demo_app.log"))
OFFSET_FILE = os.environ.get("OFFSET_FILE", os.path.join(os.path.dirname(__file__), "..", "logs", "collector_offset.json"))
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000/api/ingest")
API_KEY = os.environ.get("COLLECTOR_API_KEY", "collector-secret-api-key-live-demo-2026")
SOURCE_ID = os.environ.get("SOURCE_ID", "demo-app-live")
BATCH_SIZE = int(os.environ.get("COLLECTOR_BATCH_SIZE", "10"))
FLUSH_INTERVAL = float(os.environ.get("COLLECTOR_FLUSH_INTERVAL", "2.0"))

class LogTailer:
    def __init__(self, log_path: str = LOG_FILE, offset_path: str = OFFSET_FILE):
        self.log_path = log_path
        self.offset_path = offset_path
        self.offset = self._load_offset()

    def _load_offset(self) -> int:
        try:
            if os.path.exists(self.offset_path):
                with open(self.offset_path, "r") as f:
                    data = json.load(f)
                    return data.get("offset", 0)
        except Exception as e:
            logger.warning(f"Failed to load offset: {e}")
        return 0

    def _save_offset(self, offset: int):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.offset_path)), exist_ok=True)
            with open(self.offset_path, "w") as f:
                json.dump({"offset": offset}, f)
            self.offset = offset
        except Exception as e:
            logger.error(f"Failed to save offset: {e}")

    def read_new_lines(self) -> list:
        if not os.path.exists(self.log_path):
            return []

        lines = []
        try:
            file_size = os.path.getsize(self.log_path)
            # If file was truncated, reset offset
            if file_size < self.offset:
                self.offset = 0

            with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self.offset)
                new_content = f.read()
                new_offset = f.tell()

                if new_content:
                    lines = [l for l in new_content.splitlines() if l.strip()]
                    self._save_offset(new_offset)
        except Exception as e:
            logger.error(f"Error reading log file: {e}")

        return lines

    def send_batch(self, lines: list) -> bool:
        if not lines:
            return True

        # Parse JSON lines or encapsulate plain strings
        raw_events = []
        for line in lines:
            line_str = line.strip()
            if line_str.startswith("{") and line_str.endswith("}"):
                try:
                    obj = json.loads(line_str)
                    raw_events.append(obj)
                    continue
                except Exception:
                    pass
            raw_events.append({"message": line_str, "service": "demo-app", "severity": "INFO"})

        payload = {
            "sourceId": SOURCE_ID,
            "events": raw_events
        }

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        }

        # Retry with backoff
        for attempt in range(3):
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(BACKEND_URL, json=payload, headers=headers)
                    if resp.status_code == 200:
                        logger.info(f"Successfully forwarded batch of {len(raw_events)} events to {BACKEND_URL}")
                        return True
                    else:
                        logger.warning(f"Backend returned HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                time.sleep(1.0 * (attempt + 1))

        return False

    def run_once(self) -> int:
        lines = self.read_new_lines()
        if lines:
            self.send_batch(lines)
        return len(lines)

    def run_loop(self):
        logger.info(f"Collector tailing {self.log_path} -> {BACKEND_URL}")
        while True:
            self.run_once()
            time.sleep(FLUSH_INTERVAL)

if __name__ == "__main__":
    tailer = LogTailer()
    tailer.run_loop()
