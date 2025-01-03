import http.client
import json
import os
from dotenv import load_dotenv

load_dotenv()


class SerperClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("Serper_api")
        self.base_url = "google.serper.dev"
        self.headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

    def _make_request(self, endpoint, payload):
        conn = http.client.HTTPSConnection(self.base_url)
        conn.request("POST", endpoint, payload, self.headers)
        res = conn.getresponse()
        data = res.read()
        return data.decode("utf-8")

    def search_query(self, query):
        payload = json.dumps({"q": query})
        return self._make_request("/search", payload)

    def image_query(self, keywords):
        payload = json.dumps({
            "q": keywords,
            "gl": "in",
            "type": "images",
            "engine": "google",
            "num": 10
        })
        return self._make_request("/images", payload)


# Example usage:
# serper_client = SerperClient()
# print(serper_client.search_query("example query"))
# print(serper_client.image_query("example keywords"))