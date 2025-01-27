import re
import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
from typing import Dict, List, Optional


class Scraper:
    def __init__(self):
        self._html_tags = re.compile(r'<[^>]+>')
        self._whitespace = re.compile(r'\s+')
        self._non_printable = re.compile(r'[^\x20-\x7E]')

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
        # Basic cleaning
        text = self._html_tags.sub(' ', text)  # Remove HTML tags
        text = text.replace('\n', ' ').replace('\t', ' ')
        text = self._whitespace.sub(' ', text).strip()
        
        # Advanced cleaning
        if remove_special:
            text = re.sub(r'[^a-zA-Z0-9\s.,!?\-&\'"]', '', text)
        if lowercase:
            text = text.lower()
            
        # Remove non-printable characters
        text = self._non_printable.sub(' ', text)
        return text

    def content_extractor(self, response: bytes, 
                         max_paragraphs: int = 20,
                         max_headings: int = 10) -> Dict[str, List[str]]:
        """
        Extract and process content from HTML response
        Args:
            response: HTML bytes content
            max_paragraphs: Maximum paragraphs to return
            max_headings: Maximum headings to return
        Returns:
            Dictionary containing processed content
        """
        soup = BeautifulSoup(response, 'html.parser')
        if not soup:
            return {}

        # Extract and process paragraphs
        paragraphs = [
            self._process_text(p.text) 
            for p in soup.find_all('p')[:max_paragraphs]
        ]

        # Extract and process headings
        headings = [
            self._process_text(h.text)
            for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])[:max_headings]
        ]

        return {
            "paragraphs": paragraphs,
            "headings": headings,
            "cleaned_text": self._process_text(soup.get_text()),
            "domain_info": {
                "title": self._process_text(soup.title.string) if soup.title else "",
                "meta_description": self._process_text(
                    soup.find("meta", {"name": "description"})["content"]
                ) if soup.find("meta", {"name": "description"}) else ""
            }
        }

    def get_website_content(self, link: str, 
                           timeout: int = 10, 
                           headers: Optional[Dict] = None,
                           max_paragraphs: int = 20,
                           max_headings: int = 10) -> Dict:
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
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.5'
        }

        try:
            response = requests.get(
                url=link,
                headers=headers or default_headers,
                timeout=timeout,
                allow_redirects=True,
                stream=True
            )
            response.raise_for_status()

            # Check content type before processing
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type:
                raise ValueError(f"Unsupported content type: {content_type}")

            return self.content_extractor(
                response.content,
                max_paragraphs=max_paragraphs,
                max_headings=max_headings
            )

        except RequestException as e:
            raise RequestException(f"Network error fetching {link}: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Error processing {link}: {str(e)}") from e