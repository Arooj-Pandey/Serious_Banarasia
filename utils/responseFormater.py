from typing import Dict, List, Optional
from tools.scraperTool import Scraper
import re
import logging
from datetime import datetime

class ResponseFormatter:
    def __init__(self, json_data: Dict, max_content_length: int = 2000):
        self.json_data = json_data
        self.scraper = Scraper()
        self.max_content_length = max_content_length
        self.logger = logging.getLogger(__name__)
        
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Smart truncation that preserves sentence boundaries"""
        if len(text) <= max_length:
            return text
            
        # Find the last sentence end within limit
        truncated = text[:max_length]
        last_sentence_end = max(
            truncated.rfind(". "),
            truncated.rfind("! "),
            truncated.rfind("? ")
        )
        
        return truncated[:last_sentence_end+1] if last_sentence_end != -1 else truncated + "..."

    def _process_organic_result(self, result: Dict) -> Optional[Dict]:
        """Process and enrich a single organic search result"""
        try:
            link = result.get('link', '')
            if not link.startswith(('http://', 'https://')):
                return None

            scraped_content = {}
            try:
                scraped_content = self.scraper.get_website_content(
                    link,
                    max_paragraphs=5,
                    max_headings=3
                )
            except Exception as e:
                self.logger.warning(f"Scraping failed for {link}: {str(e)}")

            # Create structured content
            return {
                'title': self._truncate_text(result.get('title', ''), 120),
                'domain': re.sub(r'^www\.', '', re.search(r'https?://([^/]+)', link).group(1)),
                'link': link,
                'snippet': self._truncate_text(result.get('snippet', ''), 300),
                'content': {
                    'key_points': scraped_content.get('headings', [])[:3],
                    'main_content': [
                        self._truncate_text(p, 500) 
                        for p in scraped_content.get('paragraphs', [])[:5]
                    ],
                    'meta_description': scraped_content.get('domain_info', {}).get('meta_description', ''),
                    'last_updated': datetime.now().strftime('%Y-%m-%d')
                },
                'position': result.get('position', 999),
                'source_quality': self._assess_source_quality(link)
            }
        except Exception as e:
            self.logger.error(f"Error processing result: {str(e)}")
            return None

    def _assess_source_quality(self, url: str) -> str:
        """Simple heuristic for source quality assessment"""
        domain = url.split('/')[2]
        if any(d in domain for d in ['gov', 'edu', 'org']):
            return 'high'
        if any(d in domain for d in ['wikipedia', 'who.int']):
            return 'high'
        return 'medium'

    def format_for_llm(self) -> Dict:
        """Main formatting method that structures data for LLM consumption"""
        formatted_data = {
            'metadata': {
                'processing_date': datetime.now().isoformat(),
                'sources_used': 0,
                'total_content_length': 0
            },
            'organic_results': [],
            'image_results': [],
            'knowledge_graph': [],
            'related_questions': []
        }

        try:
            for api_type, responses in self.json_data.items():
                for response in responses:
                    query = next(iter(response))
                    results = response[query]

                    if 'organic' in results:
                        for result in results['organic']:
                            processed = self._process_organic_result(result)
                            if processed:
                                formatted_data['organic_results'].append(processed)
                                formatted_data['metadata']['sources_used'] += 1

                    if 'images' in results:
                        formatted_data['image_results'].extend([
                            {
                                'title': img.get('title', ''),
                                'url': img.get('imageUrl', ''),
                                'context': self._truncate_text(img.get('snippet', ''), 200)
                            } for img in results['images']
                        ])

                    if 'peopleAlsoAsk' in results:
                        formatted_data['related_questions'].extend([
                            {
                                'question': q.get('question', ''),
                                'summary': self._truncate_text(q.get('snippet', ''), 300),
                                'sources': [{'title': q.get('title', ''), 'url': q.get('link', '')}]
                            } for q in results.get('peopleAlsoAsk', [])
                        ])

            # Sort results by position and quality
            formatted_data['organic_results'].sort(
                key=lambda x: (x['position'], 0 if x['source_quality'] == 'high' else 1)
            )

            # Calculate total content length
            content_str = str(formatted_data)
            formatted_data['metadata']['total_content_length'] = len(content_str)
            
            if len(content_str) > self.max_content_length:
                self.logger.warning(f"Formatted content exceeds {self.max_content_length} characters")

        except Exception as e:
            self.logger.error(f"Formatting failed: {str(e)}")
            return {'error': 'Failed to process search results'}

        return formatted_data