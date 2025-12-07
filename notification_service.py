import sqlite3
import json
import time
import os
from dotenv import load_dotenv
from pywebpush import webpush, WebPushException

load_dotenv()

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_CLAIMS = {
    "sub": "mailto:lzhoang2302@gmail.com"
}

class NotificationService:
    def __init__(self, vote_crawler):
        self.fc_vote_crawler = vote_crawler
        self.init_db()
        
        self.nominee_metadata = {
            "w27-83": {"name": "Anh Trai Vượt Ngàn Chông Gai - Techcombank", "image": "https://event.mediacdn.vn/zoom/80_80/257767050295742464/image/fc/2025/11/29/photo2025-11-2817-17-50-2-17643880977201950529428.jpg"},
            "w27-80": {"name": "Chuỗi concert G-DRAGON - VPBank", "image": "https://event.mediacdn.vn/zoom/80_80/257767050295742464/image/fc/2025/11/25/logovpb-17640426113382097448848.png"},
            "w27-82": {"name": "Em Xinh Say Hi - TPBank", "image": "https://event.mediacdn.vn/zoom/80_80/257767050295742464/image/fc/2025/11/25/logo-vuong2-49-17640573719781603453757.jpg"},
            "w27-79": {"name": "Anh Trai Say Hi - VIB", "image": "https://event.mediacdn.vn/zoom/80_80/257767050295742464/image/fc/2025/11/28/photo2025-11-2810-12-52-17642997610201243588107.jpg"},
            "w27-81": {"name": "Sao Nhập Ngũ - MBBank", "image": "https://event.mediacdn.vn/zoom/80_80/257767050295742464/image/fc/2025/11/25/logo-vuong2-40-1764057371955171660827.jpg"},
            "w27-78": {"name": "Live Concert 2025 - See The Light - SeABank", "image": "https://event.mediacdn.vn/zoom/80_80/257767050295742464/image/fc/2025/11/25/logo-vuong2-62-17640822516411947393111.jpg"}
        }

    def init_db(self):
        conn = sqlite3.connect('subscribers.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS subscribers
                     (endpoint TEXT PRIMARY KEY, p256dh TEXT, auth TEXT)''')
        conn.commit()
        conn.close()

    def add_subscriber(self, sub_info):
        try:
            if not sub_info or 'endpoint' not in sub_info:
                return False, "Invalid subscription"

            endpoint = sub_info['endpoint']
            keys = sub_info.get('keys', {})
            p256dh = keys.get('p256dh')
            auth = keys.get('auth')

            conn = sqlite3.connect('subscribers.db', check_same_thread=False)
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO subscribers (endpoint, p256dh, auth) VALUES (?, ?, ?)", (endpoint, p256dh, auth))
            conn.commit()
            conn.close()
            print(f"New subscriber saved: {endpoint[:20]}...")
            return True, "Success"
        except Exception as e:
            return False, str(e)

    def get_vapid_public_key(self):
        return VAPID_PUBLIC_KEY

    def get_all_subscriptions(self):
        conn = sqlite3.connect('subscribers.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM subscribers")
        rows = c.fetchall()
        conn.close()
        
        subs = []
        for row in rows:
            subs.append({
                "endpoint": row['endpoint'],
                "keys": {
                    "p256dh": row['p256dh'],
                    "auth": row['auth']
                }
            })
        return subs

    def remove_subscription(self, endpoint):
        conn = sqlite3.connect('subscribers.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("DELETE FROM subscribers WHERE endpoint = ?", (endpoint,))
        conn.commit()
        conn.close()

    def send_push_notification(self, message_body):
        subscribers = self.get_all_subscriptions()
        if not subscribers:
            return

        print(f"Sending push to {len(subscribers)} subscribers...")
        
        for sub in subscribers:
            try:
                webpush(
                    subscription_info=sub,
                    data=json.dumps(message_body),
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims=VAPID_CLAIMS,
                    ttl=60
                )
            except WebPushException as ex:
                if ex.response and ex.response.status_code in [400, 410]:
                    print(f"Removing invalid subscription (status {ex.response.status_code}): {sub['endpoint'][:30]}...")
                    self.remove_subscription(sub['endpoint'])
                elif "400 Bad Request" in str(ex) or "410 Gone" in str(ex):
                     print(f"Removing invalid subscription (error message): {sub['endpoint'][:30]}...")
                     self.remove_subscription(sub['endpoint'])
                else:
                    print(f"Push failed: {ex}")
            except Exception as e:
                print(f"Error sending push: {e}")

    def run(self):
        prev_votes = {}
        last_summary_time = time.time()

        while True:
            try:
                current_votes = self.fc_vote_crawler.get_latest_votes()
                
                if not current_votes:
                    time.sleep(10)
                    continue
                
                if not prev_votes:
                    prev_votes = current_votes.copy()
                    time.sleep(10)
                    continue

                nominee_ids = list(self.nominee_metadata.keys())
                
                curr_ranking = sorted(nominee_ids, key=lambda x: current_votes.get(x, 0), reverse=True)
                prev_ranking = sorted(nominee_ids, key=lambda x: prev_votes.get(x, 0), reverse=True)
                
                now = time.time()
                if now - last_summary_time >= 600:
                    if len(curr_ranking) >= 2:
                        top1_id = curr_ranking[0]
                        top2_id = curr_ranking[1]
                        
                        top1_votes = current_votes.get(top1_id, 0)
                        top2_votes = current_votes.get(top2_id, 0)
                        gap = top1_votes - top2_votes
                        
                        top1_meta = self.nominee_metadata.get(top1_id, {})
                        top1_name = top1_meta.get("name", top1_id)
                        top1_image = top1_meta.get("image", "https://static.mediacdn.vn/fchoice/images/logo.svg")
                        
                        self.send_push_notification({
                            "title": "Cập nhật đường đua FChoice 2025",
                            "body": f"🏆 Dẫn đầu: {top1_name}\n📈 Tổng vote: {top1_votes:,}\n⚡ Tạo khoảng cách: {gap:,} vote",
                            "icon": top1_image
                        })
                        print(f"Push Sent: Race Summary")
                        last_summary_time = now

                for rank_index, nid in enumerate(curr_ranking):
                    prev_rank_index = -1
                    if nid in prev_ranking:
                        prev_rank_index = prev_ranking.index(nid)
                    
                    if prev_rank_index != -1 and rank_index != prev_rank_index:
                        if rank_index < prev_rank_index:
                            meta = self.nominee_metadata.get(nid, {})
                            name = meta.get("name", nid)
                            image = meta.get("image", "https://static.mediacdn.vn/fchoice/images/logo.svg")
                            
                            title = "Biến động BXH FChoice 2025"
                            body = f"🔥 {name} vừa vươn lên vị trí #{rank_index + 1}. Vote ngay!"
                            
                            if rank_index == 0:
                                title = "👑 Ngôi vương FChoice 2025 đã đổi chủ"
                                body = f"🏆 {name} đã xuất sắc vươn lên Top 1. Cuộc đua đang cực kỳ gay cấn!"
                            
                            self.send_push_notification({
                                "title": title,
                                "body": body,
                                "icon": image
                            })
                            print(f"Push Sent: {name} rank up to #{rank_index + 1}")

                for nid in nominee_ids:
                    curr_v = current_votes.get(nid, 0)
                    prev_v = prev_votes.get(nid, 0)
                    
                    if (curr_v // 100000) > (prev_v // 100000):
                        milestone_val = (curr_v // 100000) * 100
                        meta = self.nominee_metadata.get(nid, {})
                        name = meta.get("name", nid)
                        image = meta.get("image", "https://static.mediacdn.vn/fchoice/images/logo.svg")
                        
                        self.send_push_notification({
                            "title": f"🎉 Chúc mừng {name} tại FChoice 2025",
                            "body": f"🌟 Đã cán mốc {milestone_val}K lượt bình chọn. Tiếp tục ủng hộ nào!",
                            "icon": image
                        })
                        print(f"Push Sent: {name} milestone {milestone_val}K")

                prev_votes = current_votes.copy()

            except Exception as e:
                print(f"Notification Service Error: {e}")
            
            time.sleep(10)
