from flask import Flask, jsonify, request
import fc_vote_crawler
import notification_service
from flask_cors import CORS
import threading

class FChoiceVotesAPI:
    def __init__(self):
        self.app = Flask(__name__)
        
        self._register_routes()
        CORS(self.app, resources={r"/*": {"origins": ["https://lzhoang2801.github.io", "http://127.0.0.1:3000"]}})

        self.fc_vote_crawler = fc_vote_crawler.FChoiceVoteCrawler()
        self.notification_service = notification_service.NotificationService(self.fc_vote_crawler)
        
        crawler_thread = threading.Thread(target=self.fc_vote_crawler.run, daemon=True)
        crawler_thread.start()

        notify_thread = threading.Thread(target=self.notification_service.run, daemon=True)
        notify_thread.start()

    def _register_routes(self):
        self.app.route('/get_votes')(self.api_get_votes)
        self.app.route('/subscribe', methods=['POST'])(self.api_subscribe)
        self.app.route('/unsubscribe', methods=['POST'])(self.api_unsubscribe)
        self.app.route('/vapid_public_key', methods=['GET'])(self.api_get_vapid_key)

    def api_get_votes(self):
        try:
            last_updated = request.args.get('last_updated')
            return jsonify(self.fc_vote_crawler.get_vote_history(last_updated)), 200
        except Exception as e:
            return jsonify({"error": "An unexpected error occurred"}), 500

    def api_subscribe(self):
        success, msg = self.notification_service.add_subscriber(request.json)
        if success:
            return jsonify({"success": True}), 201
        return jsonify({"error": msg}), 400

    def api_unsubscribe(self):
        try:
            data = request.json
            if data and 'endpoint' in data:
                self.notification_service.remove_subscription(data['endpoint'])
                return jsonify({"success": True}), 200
            return jsonify({"error": "Missing endpoint"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def api_get_vapid_key(self):
        return jsonify({"publicKey": self.notification_service.get_vapid_public_key()})

    def run(self, debug=True):
        self.app.run(port=5001)

if __name__ == '__main__':
    fc_votes = FChoiceVotesAPI()
    fc_votes.run()