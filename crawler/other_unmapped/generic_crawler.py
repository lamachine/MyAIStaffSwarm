import asyncio
import re
import os
import sys
# Add src directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from typing import Set, Dict, Any, Optional, List, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
import datetime
from dotenv import load_dotenv

# Import common modules
from crawler.common.storage import store_chunks
from crawler.common.text_processing import ProcessedChunk
from crawler.common.llm_provider import LLMProvider
from crawler.common.processing import process_chunk

class GenericCrawler:
    def __init__(self, 
                 start_url: str, 
                 max_pages: int = 100,
                 min_content_length: int = 100,
                 chunk_size: int = 5000,
                 max_retries: int = 3,
                 delay_between_requests: float = 0.5):
        self.start_url = start_url
        self.max_pages = max_pages
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.delay_between_requests = delay_between_requests
        self.visited_urls: Set[str] = set()
        self.failed_urls: Dict[str, str] = {}  # URL -> error message
        self.base_domain = urlparse(start_url).netloc
        
        # Configure Crawl4AI
        self.browser_config = BrowserConfig(
            headless=True,
            java_script_enabled=True
        )
        
    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain we're crawling"""
        return urlparse(url).netloc == self.base_domain
        
    def normalize_url(self, url: str, base_url: str) -> str:
        """Normalize URL to absolute form"""
        # Remove fragments and query parameters
        url = url.split('#')[0].split('?')[0]
        # Convert to absolute URL
        normalized = urljoin(base_url, url)
        # Remove trailing slashes for consistency
        return normalized.rstrip('/')
        
    def clean_content(self, content: str) -> str:
        """Clean and normalize content"""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        # Remove empty lines
        content = '\n'.join(
            line.strip() for line in content.split('\n') 
            if line.strip()
        )
        return content.strip()
        
    async def extract_links(self, html_content: str, current_url: str) -> Set[str]:
        """Extract and normalize all links from a page"""
        links = set()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all links
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Skip non-http links and anchors
            if href.startswith(('http://', 'https://', '/')):
                try:
                    normalized_url = self.normalize_url(href, current_url)
                    links.add(normalized_url)
                except Exception:
                    continue
                
        return links
        
    async def process_page(self, url: str, content: str) -> Dict[str, Any]:
        """Process a single page and extract relevant information"""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Get title
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.text.strip()
        else:
            h1_tag = soup.find('h1')
            if h1_tag:
                title = h1_tag.text.strip()
        
        # Get content (entire page)
        clean_text = self.clean_content(soup.get_text())
        
        # Structure the page data
        page_data = {
            "url": url,
            "title": title,
            "chunks": [{"text": clean_text}],
            "metadata": {
                "domain": self.base_domain,
                "crawl_time": datetime.datetime.now().isoformat(),
                "content_type": "page"
            }
        }
        
        return page_data
        
    async def crawl(self) -> Dict[str, Any]:
        """Main crawling logic"""
        results = {}
        
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            urls_to_visit = {self.start_url}
            
            while urls_to_visit and len(self.visited_urls) < self.max_pages:
                current_url = urls_to_visit.pop()
                
                if current_url in self.visited_urls:
                    continue
                    
                print(f"Crawling: {current_url}")
                
                # Implement retry logic
                for attempt in range(self.max_retries):
                    try:
                        # Configure the crawler run
                        run_config = CrawlerRunConfig(
                            cache_mode=CacheMode.BYPASS,
                            word_count_threshold=1,
                            page_timeout=30000  # 30 second timeout
                        )
                        
                        # Crawl the page
                        result = await crawler.arun(current_url, config=run_config)
                        
                        if result.success:
                            # Process the page
                            page_data = await self.process_page(current_url, result.markdown)
                            results[current_url] = page_data
                            
                            # Extract new links
                            new_links = await self.extract_links(result.markdown, current_url)
                            urls_to_visit.update(
                                url for url in new_links 
                                if url not in self.visited_urls 
                                and self.is_same_domain(url)
                            )
                            
                            # Success - break retry loop
                            break
                            
                    except Exception as e:
                        if attempt == self.max_retries - 1:  # Last attempt
                            print(f"Error crawling {current_url} after {self.max_retries} attempts: {e}")
                            self.failed_urls[current_url] = str(e)
                        await asyncio.sleep(self.delay_between_requests * (attempt + 1))
                        continue
                    
                self.visited_urls.add(current_url)
                await asyncio.sleep(self.delay_between_requests)
                    
        return {
            "results": results,
            "stats": {
                "total_pages_crawled": len(self.visited_urls),
                "successful_pages": len(results),
                "failed_pages": len(self.failed_urls),
                "failed_urls": self.failed_urls
            }
        }

async def main():
    # Load environment variables
    load_dotenv(override=True)
    
    # Get configuration from environment
    start_url = os.getenv("CURRENT_SOURCE")
    max_pages = int(os.getenv("MAX_PAGES", "50"))
    min_content_length = int(os.getenv("MIN_CONTENT_LENGTH", "200"))
    chunk_size = int(os.getenv("CHUNK_SIZE", "5000"))
    max_retries = int(os.getenv("MAX_RETRIES", "2"))
    delay_between_requests = float(os.getenv("DELAY_BETWEEN_REQUESTS", "0.5"))
    
    if not start_url:
        print("Error: CURRENT_SOURCE not set in .env file")
        return
        
    print(f"\nStarting crawl of {start_url}")
    print(f"Configuration:")
    print(f"- Max pages: {max_pages}")
    print(f"- Min content length: {min_content_length}")
    print(f"- Chunk size: {chunk_size}")
    print(f"- Max retries: {max_retries}")
    print(f"- Delay between requests: {delay_between_requests}s\n")
    
    # Initialize LLM provider
    llm_provider = LLMProvider()
    
    # Initialize crawler
    crawler = GenericCrawler(
        start_url=start_url,
        max_pages=max_pages,
        min_content_length=min_content_length,
        chunk_size=chunk_size,
        max_retries=max_retries,
        delay_between_requests=delay_between_requests
    )
    
    try:
        results = await crawler.crawl()
        
        # Process and store results using common modules
        for url, data in results['results'].items():
            chunks = data.get('chunks', [])
            for i, chunk in enumerate(chunks):
                processed_chunk = await process_chunk(
                    chunk['text'], 
                    i,
                    url,
                    llm_provider
                )
                await store_chunks([processed_chunk])
        
        # Print summary
        print(f"\nCrawl Summary:")
        print(f"Total pages attempted: {results['stats']['total_pages_crawled']}")
        print(f"Successful pages: {results['stats']['successful_pages']}")
        print(f"Failed pages: {results['stats']['failed_pages']}")
        
        if results['stats']['failed_pages'] > 0:
            print("\nFailed URLs:")
            for url, error in results['stats']['failed_urls'].items():
                print(f"- {url}: {error}")
                
    finally:
        # Cleanup
        await llm_provider.close()

if __name__ == "__main__":
    asyncio.run(main()) 