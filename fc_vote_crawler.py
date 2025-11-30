import requests
import json
from datetime import datetime
import time
import threading

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except ImportError:
    from pytz import timezone
    TZ = timezone("Asia/Ho_Chi_Minh")

class FChoiceVoteCrawler:
    def __init__(self):
        self.fc_nominee_data = {
            "w27-82": "Em Xinh Say Hi - TPBank",
            "w27-80": "Chuỗi concert G-DRAGON - VPBank",
            "w27-83": "Anh Trai Vượt Ngàn Chông Gai - Techcombank",
            "w27-78": "Live Concert 2025 - See The Light - SeABank",
            "w27-79": "Anh Trai Say Hi - VIB",
            "w27-81": "Sao Nhập Ngũ - MBBank"
        }
        self.fc_nominee_lstId = "".join(list(self.fc_nominee_data.keys()))
        self.api_url = f"https://api.fchoice.vn/vote-token.htm?m=get-vote&lstId={self.fc_nominee_lstId}&_=1764424068455"
        self.headers = {
            "Referer": "https://fchoice.vn/"
        }
        self.vote_history = self.load_vote_history()

        self.lock = threading.Lock()

    def get_current_time(self):
        return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

    def load_vote_history(self):
        try:
            with open("vote_history.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "vote_history": {},
                "last_update_time": self.get_current_time(),
            }
        except json.JSONDecodeError:
            return {
                "vote_history": {},
                "last_update_time": self.get_current_time(),
            }
        except Exception as e:
            raise Exception(f"Error loading vote history: {e}")

    def save_vote_history(self):
        try:
            with open("vote_history.json", "w") as f:
                json.dump(self.vote_history, f, indent=4)
        except Exception as e:
            raise Exception(f"Error saving vote history: {e}")

    def update_vote_history(self, nominee_id, vote_count, timestamp):
        with self.lock:
            if nominee_id not in self.fc_nominee_data:
                print(f"Skipping unknown nominee {nominee_id}.")
                return

            print(f"Updating vote history for {nominee_id} with {vote_count} votes at {timestamp}.")
            if nominee_id not in self.vote_history["vote_history"]:
                self.vote_history["vote_history"][nominee_id] = [{
                    "vote_count": vote_count,
                    "timestamp": timestamp
                }]
            else:
                self.vote_history["vote_history"][nominee_id].append({
                    "vote_count": vote_count,
                    "timestamp": timestamp
                })
            self.vote_history["last_update_time"] = timestamp

    def get_vote_history(self, last_updated=None):
        with self.lock:
            if last_updated is None:
                import copy
                return copy.deepcopy(self.vote_history)
            
            filtered_data = {
                "vote_history": {},
                "last_update_time": self.vote_history.get("last_update_time")
            }
            
            for nominee_id, votes in self.vote_history.get("vote_history", {}).items():
                new_votes = [v for v in votes if v["timestamp"] > last_updated]
                if new_votes:
                    filtered_data["vote_history"][nominee_id] = new_votes
            
            return filtered_data

    def crawl_votes(self):
        try:
            timestamp = self.get_current_time()
            response = requests.get(self.api_url, headers=self.headers)
            text = response.text
            data = json.loads(text)
            
            if data["Success"] and data["Data"]:
                for item in data["Data"]:
                    m = item["m"]
                    a = item["a"]
                    v = item["list"][0]["v"]
                    nominee_id = "w{a}-{m}".format(a=a, m=m)
                    self.update_vote_history(nominee_id, v, timestamp)
            self.save_vote_history()
        except json.JSONDecodeError:
            print("Invalid JSON response")
        except Exception as e:
            print(f"Error: {e}")

    def run(self):
        while True:
            now = datetime.now(TZ)
            if now.second % 10 == 0:
                try:
                    self.crawl_votes()
                except Exception as e:
                    print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    crawler = FChoiceVoteCrawler()
    crawler.run()