import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()


class SerperClient:
    def __init__(self, api_key=str):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.base_url = "https://google.serper.dev"
        self.headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

    def _make_request(self, endpoint, payload):
        response = requests.request("POST", self.base_url + endpoint, headers=self.headers, data=payload)
        return response.text

    def search_query(self, query):
        payload = json.dumps({
            "q": query,
            "gl" :"in" # Location   # "gl": "in" for India
            })
        return self._make_request("/search", payload)

    def image_query(self, keywords):
        payload = json.dumps({
            "q": keywords,
            "gl": "in" # Location   # "gl": "in" for India
        })
        return self._make_request("/images", payload)


# Example usage:
# serper_client = SerperClient()
# print(serper_client.search_query("example query"))
# print(serper_client.image_query("example keywords"))