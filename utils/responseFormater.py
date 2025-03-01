from typing import Dict, List, Optional
from tools.scraperTool import Scraper
import re
import logging
from datetime import datetime
import concurrent.futures
import asyncio
import time

class ResponseFormatter:
    def __init__(self, json_data: Dict, max_content_length: int = 2000):
        self.json_data = json_data
        self.scraper = Scraper()
        self.max_content_length = max_content_length
        self.logger = logging.getLogger(__name__)
        
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Smart truncation that preserves sentence boundaries"""
        if not text or len(text) <= max_length:
            return text or ""
            
        # Find the last sentence end within limit
        truncated = text[:max_length]
        last_sentence_end = max(
            truncated.rfind(". "),
            truncated.rfind("! "),
            truncated.rfind("? ")
        )
        
        return truncated[:last_sentence_end+1] if last_sentence_end != -1 else truncated + "..."

    def _process_organic_result(self, result: Dict, scrape_timeout: int = 3) -> Optional[Dict]:
        """Process and enrich a single organic search result with limited scraping time"""
        try:
            link = result.get('link', '')
            if not link.startswith(('http://', 'https://')):
                return None

            # Skip scraping for certain domains that are slow or problematic
            skip_scraping = any(domain in link for domain in [
                'pdf', 'youtube.com', 'facebook.com', 'instagram.com', 
                'twitter.com', 'linkedin.com'
            ])
            
            scraped_content = {}
            if not skip_scraping:
                try:
                    # Use a shorter timeout for scraping
                    start_time = time.time()
                    scraped_content = self.scraper.get_website_content(
                        link,
                        timeout=scrape_timeout,  # Reduced from default 10 seconds
                        max_paragraphs=1,        # Reduced from 2
                        max_headings=1
                    )
                    self.logger.info(f"Scraped {link} in {time.time() - start_time:.2f} seconds")
                except Exception as e:
                    self.logger.warning(f"Scraping failed for {link}: {str(e)}")
                    # If scraping fails, don't let it block the response

            # Use original snippet if scraping failed or was skipped
            main_content = scraped_content.get('paragraphs', [])
            if not main_content and result.get('snippet'):
                main_content = [result.get('snippet')]

            # Extract domain safely
            domain = "unknown"
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', link)
            if domain_match:
                domain = re.sub(r'^www\.', '', domain_match.group(1))

            # Create structured content
            return {
                'title': self._truncate_text(result.get('title', ''), 80),  # Reduced from 120
                'domain': domain,
                'link': link,
                'snippet': self._truncate_text(result.get('snippet', ''), 200),  # Reduced from 300
                'content': {
                    'key_points': scraped_content.get('headings', [])[:1],  # Reduced from 3 to 1
                    'main_content': [
                        self._truncate_text(p, 300)  # Reduced from 500 
                        for p in main_content[:2]     # Reduced from 5 to 2
                    ],
                    'meta_description': scraped_content.get('domain_info', {}).get('meta_description', '')[:150],  # Limited to 150 chars
                    'last_updated': datetime.now().strftime('%Y-%m-%d')
                },
                'position': result.get('position', 999),
                'source_quality': self._assess_source_quality(link)
            }
        except Exception as e:
            self.logger.error(f"Error processing result: {str(e)}")
            # Return a basic result rather than None to ensure we always have something
            return {
                'title': result.get('title', 'Information'),
                'domain': 'unknown',
                'link': result.get('link', ''),
                'snippet': result.get('snippet', 'Information'),
                'content': {
                    'key_points': [],
                    'main_content': [result.get('snippet', 'Information')],
                    'meta_description': '',
                    'last_updated': datetime.now().strftime('%Y-%m-%d')
                },
                'position': result.get('position', 999),
                'source_quality': 'medium'
            }

    def _assess_source_quality(self, url: str) -> str:
        """Simple heuristic for source quality assessment"""
        domain = url.split('/')[2] if len(url.split('/')) > 2 else ""
        if any(d in domain for d in ['gov', 'edu', 'org']):
            return 'high'
        if any(d in domain for d in ['wikipedia', 'who.int']):
            return 'high'
        return 'medium'

    def _process_organic_results_parallel(self, results: List[Dict], max_workers: int = 3) -> List[Dict]:
        """Process organic results in parallel with a timeout"""
        processed_results = []
        
        if not results:
            return processed_results
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._process_organic_result, result, 3): result 
                      for result in results[:5]}
            
            for future in concurrent.futures.as_completed(futures, timeout=8):
                try:
                    processed = future.result()
                    if processed:
                        processed_results.append(processed)
                except concurrent.futures.TimeoutError:
                    self.logger.warning("Parallel processing timed out")
                    break
                except Exception as e:
                    self.logger.error(f"Parallel processing error: {str(e)}")
                    
                if len(processed_results) >= 3:
                    for f in futures:
                        f.cancel()
                    break
                    
        return processed_results

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
            if not self.json_data or not isinstance(self.json_data, dict):
                self.logger.warning("Invalid or empty JSON data received")
                return formatted_data

            for api_type, responses in self.json_data.items():
                if not responses:
                    continue
                    
                for response_idx, response in enumerate(responses[:2]):
                    query = next(iter(response))
                    results = response[query]

                    if 'organic' in results:
                        processed_results = self._process_organic_results_parallel(
                            results['organic'], 
                            max_workers=3
                        )
                        formatted_data['organic_results'].extend(processed_results)
                        formatted_data['metadata']['sources_used'] += len(processed_results)

                    if 'images' in results and api_type == 'image_api':
                        formatted_data['image_results'].extend([{
                            'title': img.get('title', '')[:50],
                            'url': img.get('imageUrl', ''),
                            'context': self._truncate_text(img.get('snippet', ''), 100)
                        } for img in results['images'][:3]])

                    if 'peopleAlsoAsk' in results:
                        formatted_data['related_questions'].extend([{
                            'question': q.get('question', '')[:80],
                            'summary': self._truncate_text(q.get('snippet', ''), 150),
                            'sources': [{'title': q.get('title', '')[:50], 'url': q.get('link', '')}]
                        } for q in results.get('peopleAlsoAsk', [])[:2]])

            formatted_data['organic_results'].sort(
                key=lambda x: (x['position'], 0 if x['source_quality'] == 'high' else 1)
            )
            
            if len(formatted_data['organic_results']) > 3:
                formatted_data['organic_results'] = formatted_data['organic_results'][:3]

            content_str = str(formatted_data)
            formatted_data['metadata']['total_content_length'] = len(content_str)
            
            if len(content_str) > self.max_content_length:
                self.logger.warning(f"Formatted content exceeds {self.max_content_length} characters")
                for result in formatted_data['organic_results']:
                    result['content']['main_content'] = result['content']['main_content'][:1]

        except Exception as e:
            self.logger.error(f"Formatting failed: {str(e)}")
            
        return formatted_data