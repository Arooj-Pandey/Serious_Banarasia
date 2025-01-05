from typing import Dict, List


class Utils:
    def __init__(self, json_data):
        self.json_data = json_data        

    def parse_api_results(json_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Parse and clean API results."""
        parsed_results: Dict[str, List[Dict]] = {}
        
        try:
            for api_type, responses in json_data.items():
                parsed_results[api_type] = []
                
                for response in responses:
                    try:
                        query = next(iter(response))
                        results = response[query]
                        cleaned_results = []

                        if 'organic' in results:
                            # Handle text search results
                            for result in results['organic']:
                                cleaned_results.append({
                                    'title': result.get('title', ''),
                                    'link': result.get('link', ''),
                                    'snippet': result.get('snippet', '')
                                })
                        elif 'images' in results:
                            # Handle image search results
                            for result in results['images']:
                                cleaned_results.append({
                                    'title': result.get('title', ''),
                                    'imageUrl': result.get('imageUrl', '')
                                })
                                
                        if cleaned_results:
                            parsed_results[api_type].append({'results': cleaned_results})
                            
                    except Exception as e:
                        print(f"Error parsing {api_type} response: {str(e)}")
                        continue
                        
        except Exception as e:
            print(f"Error parsing results: {str(e)}")
            return {}
            
        return parsed_results