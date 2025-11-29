from flask import Flask, jsonify, request
import fc_vote_crawler
from flask_cors import CORS
import threading

class FChoiceVotesAPI:
    def __init__(self):
        self.app = Flask(__name__)
        self._register_routes()
        CORS(self.app, resources={r"/*": {"origins": ["https://lzhoang2801.github.io", "http://127.0.0.1:3000"]}})

        self.fc_vote_crawler = fc_vote_crawler.FChoiceVoteCrawler()
        
        crawler_thread = threading.Thread(target=self.fc_vote_crawler.run, daemon=True)
        crawler_thread.start()

    def _register_routes(self):
        self.app.route('/get_votes')(self.api_get_votes)

    def api_get_votes(self):
        try:
            last_updated = request.args.get('last_updated')
            return jsonify(self.fc_vote_crawler.get_vote_history(last_updated)), 200
        except Exception as e:
            print(f"API Error: {e}")
            return jsonify({"error": "An unexpected error occurred"}), 500

    def run(self, debug=True):
        self.app.run(port=5001)

if __name__ == '__main__':
    fc_votes = FChoiceVotesAPI()
    fc_votes.run()