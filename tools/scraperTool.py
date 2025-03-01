import re
import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import time
import random
import logging


class Scraper:
    def __init__(self):
        self._html_tags = re.compile(r'<[^>]+>')
        self._whitespace = re.compile(r'\s+')
        self._non_printable = re.compile(r'[^\x20-\x7E]')
        self._user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36'
        ]
        self._cache = {}

    def _process_text(self, text: str, 
                     lowercase: bool = False,
                     remove_special: bool = True) -> str:
        """
        Clean and normalize text content
        Args:
            text: Input text to process
            lowercase: Convert to lowercase
            remove_special: Remove special characters
        Returns:
            Processed text string
        """
        if not text:
            return ""
            
        text = self._html_tags.sub(' ', text)  
        text = text.replace('\n', ' ').replace('\t', ' ')
        text = self._whitespace.sub(' ', text).strip()
        
        if remove_special:
            text = re.sub(r'[^\w\s.,!?\-&\'"]', '', text)
        if lowercase:
            text = text.lower()
            
        text = self._non_printable.sub(' ', text)
        return text

    def content_extractor(self, response: bytes, 
                         max_paragraphs: int = 5,
                         max_headings: int = 5) -> Dict[str, List[str]]:
        """
        Extract and process content from HTML response
        Args:
            response: HTML bytes content
            max_paragraphs: Maximum paragraphs to return
            max_headings: Maximum headings to return
        Returns:
            Dictionary containing processed content
        """
        soup = BeautifulSoup(response, 'lxml')
        if not soup:
            return {}

        main_content = soup.find_all(['main', 'article', 'div', 'section'])
        target = soup
        if main_content:
            target = max(main_content, key=lambda x: len(x.get_text()), default=soup)

        paragraphs = []
        for p in target.find_all('p'):
            if len(paragraphs) >= max_paragraphs:
                break
            clean_text = self._process_text(p.text)
            if clean_text and len(clean_text) > 40:  
                paragraphs.append(clean_text)

        headings = []
        for h in target.find_all(['h1', 'h2', 'h3'])[:max_headings]:  
            clean_text = self._process_text(h.text)
            if clean_text and len(clean_text) > 5:  
                headings.append(clean_text)

        title = soup.title.string if soup.title else ""
        meta_desc = ""
        meta_tag = soup.find("meta", {"name": "description"})
        if meta_tag and "content" in meta_tag.attrs:
            meta_desc = meta_tag["content"]

        return {
            "paragraphs": paragraphs,
            "headings": headings,
            "domain_info": {
                "title": self._process_text(title),
                "meta_description": self._process_text(meta_desc)
            }
        }

    def get_website_content(self, link: str, 
                           timeout: int = 5, 
                           headers: Optional[Dict] = None,
                           max_paragraphs: int = 5,
                           max_headings: int = 5) -> Dict:
        """
        Fetch and process website content
        Args:
            link: URL to scrape
            timeout: Request timeout in seconds
            headers: Custom headers dictionary
            max_paragraphs: Limit number of paragraphs returned
            max_headings: Limit number of headings returned
        Returns:
            Dictionary with processed content
        Raises:
            RequestException: For network-related errors
        """
        cache_key = f"{link}_{max_paragraphs}_{max_headings}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        if not link.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid URL format: {link}")
            
        skip_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', 
                          '.jpg', '.jpeg', '.png', '.gif', '.mp3', '.mp4', '.avi', '.mov']
        if any(link.endswith(ext) for ext in skip_extensions):
            raise ValueError(f"Skipping binary/media file: {link}")

        default_headers = {
            'User-Agent': random.choice(self._user_agents),
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Connection': 'keep-alive',
            'DNT': '1'
        }

        start_time = time.time()
        try:
            response = requests.get(
                url=link,
                headers=headers or default_headers,
                timeout=timeout,
                allow_redirects=True,
                stream=True
            )
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
                raise ValueError(f"Unsupported content type: {content_type}")

            content_length = int(response.headers.get('Content-Length', 0))
            if content_length > 1_000_000:  
                soup = BeautifulSoup("<html><head><title>Large Page</title></head><body></body></html>", 'lxml')
                result = {
                    "paragraphs": ["This page is too large to process quickly."],
                    "headings": [],
                    "domain_info": {
                        "title": response.url.split('/')[-1],
                        "meta_description": f"Large page ({content_length/1000:.1f}KB)"
                    }
                }
            else:
                result = self.content_extractor(
                    response.content,
                    max_paragraphs=max_paragraphs,
                    max_headings=max_headings
                )
                
            self._cache[cache_key] = result
            return result

        except RequestException as e:
            raise RequestException(f"Network error fetching {link}: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Error processing {link}: {str(e)}") from e
        finally:
            processing_time = time.time() - start_time
            if processing_time > 2:  
                logging.getLogger(__name__).warning(f"Slow scraping for {link}: {processing_time:.2f}s")