from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import os
from dotenv import load_dotenv
import streamlit as st
from tools.serper import SerperClient
from models.gemini import GeminiModel

# Load environment variables
load_dotenv()


class QueryRouter:
    def __init__(self, serper_api_key):
        """
        Initialize the QueryRouter with keywords and the Serper API key.

        :param keywords: dict containing categories (e.g., 'text_api', 'image_api') and associated keywords.
        :param serper_api_key: API key for the SerperClient.
        """
        self.serper_client = SerperClient(api_key=serper_api_key)
        self.results_file = Path("results.json")   # Define a path for storing results

    def route_keywords(self, keywords):
        """
        Route keywords to appropriate search APIs and return the results.

        :return: dict containing results categorized by API type.
        """
        results = {"image_api": [], "search_api": []}

        # Filter out control parameters
        categories = {k: v for k, v in keywords.items() if k != 'api_needed'}

        for category, keyword_list in categories.items():
            if category not in results:
                print(f"Unknown category: {category}")
                continue

            for keyword in keyword_list:
                try:
                    # Route to appropriate API
                    if category in "search_api": 
                        result = self.serper_client.search_query(keyword)
                        print(result)
                    elif category == "image_api":
                        result = self.serper_client.image_query(keyword)
                    else:
                        continue

                    # Parse and validate response
                    if isinstance(result, str):
                        result = json.loads(result)
                    results[category].append({keyword: result})

                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON for {keyword}: {str(e)}")
                except Exception as e:
                    print(f"Error processing {keyword}: {str(e)}")

        # Save results to file
        try:
            self.results_file.write_text(
                json.dumps(results, indent=4, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as e:
            print(f"Error saving results: {str(e)}")

        return results