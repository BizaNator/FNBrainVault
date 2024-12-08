from urllib.parse import urlparse
import nodriver as uc
import asyncio
import os
import aiohttp
import time
import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import yaml
import shutil
import json
from typing import Dict, List, Tuple, Optional
import signal
import pickle
from dataclasses import dataclass, asdict, field
import sys
from combine_docs import DocumentProcessor
from book_formatter import BookFormatter
from markdown_utils import MarkdownProcessor
from markdownify import markdownify as md
from config_manager import ConfigManager

# Configuration
#BASE_URL = "https://dev.epicgames.com/documentation/en-us/uefn/unreal-editor-for-fortnite-documentation"
#BASE_URL = "https://dev.epicgames.com/documentation/en-us/fortnite-creative/fortnite-creative-documentation"
OUTPUT_DIR = ConfigManager().get_setting("output_dir")
#IMAGES_DIR = "./downloaded_docs/images"
#MAX_CONCURRENT_DOWNLOADS = 5
#RATE_LIMIT_DELAY = 0.5  # seconds between requests
LOG_FILE = "webmark_uefn.log"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

@dataclass
class DownloadState:
    completed_urls: set[str]
    failed_downloads: Dict[str, Tuple[int, str]]
    retry_queue: List[str]
    
    def save(self, output_dir: str):
        state_file = Path(output_dir) / '.download_state'
        with open(state_file, 'wb') as f:
            pickle.dump(asdict(self), f)
    
    @classmethod
    def load(cls, output_dir: str) -> Optional['DownloadState']:
        state_file = Path(output_dir) / '.download_state'
        if state_file.exists():
            with open(state_file, 'rb') as f:
                data = pickle.load(f)
                return cls(**data)
        return None

@dataclass
class DownloadStatus:
    url: str
    status_code: int
    retry_count: int
    last_attempt: datetime
    error_message: str = ""

@dataclass
class DownloadError:
    url: str
    error_type: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)

class DownloadManager:
    def __init__(self: str = None):
        # Use provided output_dir or get from config
        self.output_dir = ConfigManager().get_setting("output_dir")
        self.max_retries = ConfigManager().get_setting("retry_attempts")
        self.retry_delay = ConfigManager().get_setting("rate_limit_delay")
        self.failed_downloads: Dict[str, Tuple[int, str]] = {}
        self.retry_queue: List[str] = []
        self.completed_urls: set[str] = set()
        self.is_shutting_down = False
        self.processed_urls: set[str] = set()
        self.download_times: List[float] = []
        self.failed_urls: set[str] = set()
        self.status_map: Dict[str, DownloadStatus] = {}
        self.status_file = Path(self.output_dir) / '.download_status.json'
        self.recursion_errors: Dict[str, DownloadError] = {}
        self.max_recursion_retries = ConfigManager().get_setting("max_recursion_retries")
        self.markdown_processor = MarkdownProcessor(self.output_dir)
        
        # Load previous states
        if state := DownloadState.load(self.output_dir):
            self.completed_urls = state.completed_urls
            self.failed_downloads = state.failed_downloads
            self.retry_queue = state.retry_queue
            logging.info(f"Resumed from previous state. Completed: {len(self.completed_urls)}")
        
        self.load_status()

    def save_state(self):
        """Save current download state"""
        state = DownloadState(
            completed_urls=self.completed_urls,
            failed_downloads=self.failed_downloads,
            retry_queue=self.retry_queue
        )
        state.save(self.output_dir)
        
    async def graceful_shutdown(self, sig=None):
        """Handle graceful shutdown"""
        if self.is_shutting_down:
            return
            
        self.is_shutting_down = True
        logging.info("\nInitiating graceful shutdown...")
        
        # Save current state
        self.save_state()
        self.save_failed_downloads(self.output_dir)
        
        logging.info(f"Progress saved. Completed: {len(self.completed_urls)}")
        logging.info(f"Failed: {len(self.failed_downloads)}")
        logging.info(f"Remaining in queue: {len(self.retry_queue)}")
        
        # Exit cleanly
        sys.exit(0)

    async def download_with_retry(self, session, url: str, **kwargs) -> Tuple[bool, any]:
        """Attempt to download with retries for specific status codes"""
        # Skip if already completed
        if url in self.completed_urls:
            return True, None
            
        retries = 0
        while retries < self.max_retries and not self.is_shutting_down:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        self.completed_urls.add(url)
                        self.update_sitemap(url, [], 'success')
                        return True, await response.text()
                    
                    # Server errors - should retry
                    elif response.status in [502, 503, 504]:
                        retries += 1
                        if retries < self.max_retries:
                            delay = self.retry_delay * (2 ** retries)
                            logging.warning(f"Got {response.status} for {url}, retry {retries} of {self.max_retries} (waiting {delay}s)")
                            await asyncio.sleep(delay)
                            continue
                    
                    # Client errors - generally shouldn't retry
                    elif response.status == 404:
                        logging.warning(f"Page not found: {url}")
                        self.update_sitemap(url, [], '404_not_found')
                        return False, None
                    
                    elif response.status == 429:
                        retries += 1
                        if retries < self.max_retries:
                            delay = self.retry_delay * 5
                            logging.warning(f"Rate limited on {url}, retry {retries} of {self.max_retries} (waiting {delay}s)")
                            await asyncio.sleep(delay)
                            continue
                    
                    elif response.status == 403:
                        logging.error(f"Access forbidden: {url}")
                        self.update_sitemap(url, [], '403_forbidden')
                        return False, None
                    
                    elif response.status == 401:
                        logging.error(f"Unauthorized access: {url}")
                        self.update_sitemap(url, [], '401_unauthorized')
                        return False, None
                    
                    elif response.status == 408:
                        retries += 1
                        if retries < self.max_retries:
                            logging.warning(f"Request timeout for {url}, retry {retries}")
                            await asyncio.sleep(self.retry_delay)
                            continue
                    
                    # Handle any other status codes
                    else:
                        self.failed_downloads[url] = (response.status, f"HTTP {response.status}")
                        self.retry_queue.append(url)
                        self.update_sitemap(url, [], f'failed_{response.status}')
                        logging.error(f"Failed to download {url}: HTTP {response.status}")
                        return False, None

            except aiohttp.ClientError as e:
                retries += 1
                if retries < self.max_retries:
                    logging.warning(f"Client error downloading {url}, retry {retries}: {str(e)}")
                    await asyncio.sleep(self.retry_delay)
                    continue
                
                self.failed_downloads[url] = (0, str(e))
                self.retry_queue.append(url)
                self.update_sitemap(url, [], 'client_error')
                return False, None
            
            except RecursionError as e:
                self.recursion_errors[url] = DownloadError(
                    url=url,
                    error_type="RecursionError",
                    message=str(e)
                )
                self.update_sitemap(url, [], 'recursion_error')
                return False, None
            
            except Exception as e:
                retries += 1
                if retries < self.max_retries:
                    logging.warning(f"Error downloading {url}, retry {retries}: {str(e)}")
                    await asyncio.sleep(self.retry_delay)
                    continue
                
                error_type = type(e).__name__
                self.failed_downloads[url] = (0, str(e))
                self.retry_queue.append(url)
                self.update_sitemap(url, [], f'error_{error_type}')
                logging.error(f"Failed to download {url} after {retries} retries: {str(e)}")
                return False, None

        return False, None

    def generate_index(self):
        """Generate navigation index for downloaded docs"""
        index_path = os.path.join(self.output_dir, "index.md")
        
        # Collect all markdown files
        md_files = []
        for root, _, files in os.walk(self.output_dir):
            for file in files:
                if file.endswith('.md') and file != 'index.md':
                    rel_path = os.path.relpath(os.path.join(root, file), self.output_dir)
                    md_files.append(rel_path)
        
        # Sort files for consistent ordering
        md_files.sort()
        
        # Generate index content
        content = [
            "---",
            "title: Documentation Index",
            "---",
            "",
            "# Documentation Index",
            "",
            "This index was automatically generated from downloaded documentation.",
            "",
            "## Contents",
            ""
        ]
        
        # Add file links with proper indentation based on directory structure
        for file_path in md_files:
            # Calculate indent level based on directory depth
            depth = len(Path(file_path).parent.parts)
            indent = "  " * depth
            
            # Clean up the display name
            display_name = os.path.splitext(os.path.basename(file_path))[0]
            display_name = display_name.replace('_', ' ').replace('-', ' ').title()
            
            # Add link to index
            content.append(f"{indent}- [{display_name}]({file_path})")
        
        # Write index file
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        logging.info(f"Generated index at {index_path}")

    def generate_print_ready_version(self):
        """Generate print-ready version of documentation"""
        print_dir = os.path.join(self.output_dir, "print_ready")
        os.makedirs(print_dir, exist_ok=True)
        
        # Collect all markdown files
        md_files = []
        for root, _, files in os.walk(self.output_dir):
            for file in files:
                if file.endswith('.md') and file != 'index.md':
                    md_files.append(os.path.join(root, file))
        
        # Sort files for consistent ordering
        md_files.sort()
        
        # Create single combined document
        combined_path = os.path.join(print_dir, "complete_documentation.md")
        with open(combined_path, 'w', encoding='utf-8') as combined:
            # Write header
            combined.write("---\n")
            combined.write("title: Complete Documentation\n")
            combined.write(f"date: {datetime.now().strftime('%Y-%m-%d')}\n")
            combined.write("---\n\n")
            
            # Add table of contents
            combined.write("# Table of Contents\n\n")
            for file_path in md_files:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    try:
                        if content.startswith('---'):
                            _, frontmatter, _ = content.split('---', 2)
                            metadata = yaml.safe_load(frontmatter)
                            title = metadata.get('title', os.path.basename(file_path))
                        else:
                            title = os.path.basename(file_path)
                    except:
                        title = os.path.basename(file_path)
                    
                    combined.write(f"- [{title}](#{title.lower().replace(' ', '-')})\n")
            
            combined.write("\n---\n\n")
            
            # Add content from each file
            for file_path in md_files:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    if content.startswith('---'):
                        _, _, content = content.split('---', 2)
                    
                    combined.write(content.strip())
                    combined.write("\n\n---\n\n")
        
        logging.info(f"Generated print-ready version at {combined_path}")

    def save_failed_downloads(self, output_dir: str):
        """Save failed downloads to a JSON file"""
        failed_file = os.path.join(output_dir, 'failed_downloads.json')
        with open(failed_file, 'w') as f:
            json.dump({
                'failed': self.failed_downloads,
                'retry_queue': self.retry_queue
            }, f, indent=2)

    def load_status(self):
        """Load download status from a JSON file"""
        if self.status_file.exists():
            with open(self.status_file, 'r') as f:
                self.status_map = json.load(f)
                for url, status in self.status_map.items():
                    self.failed_downloads[url] = (status['status_code'], status['error_message'])
                    self.retry_queue.append(url)
                    self.completed_urls.add(url)

    def save_status(self):
        """Save download status to a JSON file"""
        with open(self.status_file, 'w') as f:
            json.dump({
                'status': self.status_map,
                'completed_urls': list(self.completed_urls),
                'failed_downloads': self.failed_downloads,
                'retry_queue': self.retry_queue
            }, f, indent=2)

    async def retry_failed_downloads(self, session, page):
        """Retry failed downloads with different strategies"""
        if not self.recursion_errors:
            return
            
        logging.info(f"\nFound {len(self.recursion_errors)} failed downloads due to recursion errors.")
        retry = input("Would you like to retry these downloads with increased recursion limit? (y/n): ").lower()
        
        if retry != 'y':
            return
            
        # Temporarily increase recursion limit
        import sys
        original_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(5000)  # Increase limit
        
        try:
            for url, error in list(self.recursion_errors.items()):
                logging.info(f"Retrying download for: {url}")
                try:
                    await page.get(url)
                    await page.sleep(2)
                    
                    content, title = await extract_content(page, url, session, self)
                    if content and title:
                        filepath = self.markdown_processor.save_content(url, content, title)
                        logging.info(f"Successfully downloaded on retry: {filepath}")
                        del self.recursion_errors[url]
                except Exception as e:
                    logging.error(f"Still failed to download {url}: {str(e)}")
                    
        finally:
            sys.setrecursionlimit(original_limit)
            
        # Save remaining errors
        if self.recursion_errors:
            with open(os.path.join(self.output_dir, 'recursion_errors.json'), 'w') as f:
                json.dump({
                    url: asdict(error) 
                    for url, error in self.recursion_errors.items()
                }, f, indent=2)
            
            logging.warning(f"\nStill failed to download {len(self.recursion_errors)} pages.")
            logging.warning("These have been saved to recursion_errors.json for future retry.")

    def update_sitemap(self, url: str, children: List[str], status: str):
        """Update sitemap with new URL information"""
        self.sitemap.urls[url] = {
            'last_checked': datetime.now(),
            'children': children,
            'status': status
        }
        self.sitemap.last_updated = datetime.now()
        self.sitemap.save(self.output_dir)

    async def post_process_downloads(self, session, page):
        """Post-process downloaded files to ensure proper chapter organization."""
        logging.info("Post-processing downloads for chapter organization...")
        
        # Collect all markdown files
        md_files = []
        for root, _, files in os.walk(self.output_dir):
            for file in files:
                if file.endswith('.md') and file != 'index.md':
                    md_files.append(os.path.join(root, file))
        
        # Process each file
        for file_path in md_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if file already has chapter metadata
                if '---' in content and 'chapter:' in content.split('---')[1]:
                    continue
                
                # Extract URL from frontmatter
                if content.startswith('---'):
                    _, frontmatter, content = content.split('---', 2)
                    metadata = yaml.safe_load(frontmatter)
                    url = metadata.get('source_url', '')
                    
                    # Determine chapter number
                    chapter_num = self.markdown_processor.generate_chapter_number(Path(file_path))
                    if chapter_num:
                        metadata['chapter'] = chapter_num
                        
                        # Update file with new metadata
                        updated_content = f"---\n{yaml.dump(metadata)}---\n{content}"
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(updated_content)
                        
                        logging.info(f"Added chapter {chapter_num} metadata to {file_path}")
            
            except Exception as e:
                logging.error(f"Error processing {file_path}: {str(e)}")

async def extract_content(page, url, session, manager):
    """Extract content and metadata from a URL using nodriver.
    
    Args:
        page: The browser page instance
        url (str): The URL to extract content from
        session: The aiohttp session
        manager (DownloadManager): The download manager instance
    
    Returns:
        tuple[Optional[str], Optional[str]]: The markdown content and title, or None if extraction fails
    """
    try:
        print(f"Navigating to: {url}")
        await page.get(url)
        await asyncio.sleep(2)  # Changed from page.sleep to asyncio.sleep
        
        # Get title
        title = await page.evaluate("""
            document.title || 
            document.querySelector('h1')?.textContent || 
            document.querySelector('title')?.textContent || 
            'Untitled Page'
        """)
        
        # Try to get content using JavaScript
        script = """
        function getContent() {
            const selectors = [
                '.docs-content',
                '.markdown-body',
                '.article-content',
                'article',
                '.documentation-content',
                '.main-content'
            ];
            
            for (let selector of selectors) {
                const element = document.querySelector(selector);
                if (element) return element.innerHTML;
            }
            
            return document.body.innerHTML;
        }
        getContent();
        """
        
        html_content = await page.evaluate(script)
        if html_content:
            markdown_content = md(html_content).strip()
            # Process images and internal links using markdown processor
            markdown_content = await manager.markdown_processor.process_images(markdown_content, session, url)
            markdown_content = await manager.markdown_processor.process_internal_links(markdown_content, url, url)
            print("Successfully extracted content")
            return markdown_content, title
            
        return None, None
        
    except Exception as e:
        print(f"Error extracting content from {url}: {str(e)}")
        return None, None

async def get_links_and_download(page, session, manager, base_url=None, processed_urls=None, force_download=False):
    """Recursively fetch all links and download content simultaneously."""
    if processed_urls is None:
        processed_urls = set()
    
    if base_url in processed_urls:
        return []
    
    processed_urls.add(base_url)
    
    try:
        print(f"Processing: {base_url}")
        await page.get(base_url)
        await page.sleep(2)
        
        # Extract category information from the table of contents or breadcrumbs
        category_script = """
        () => {
            // First try to get category from TOC
            const tocElement = document.querySelector('[slot="documentation-toc"]');
            if (tocElement) {
                const parentLinks = tocElement.querySelectorAll('a.contents-table-link.is-parent');
                const currentPath = window.location.pathname;
                
                for (const link of parentLinks) {
                    const href = link.getAttribute('href');
                    if (currentPath.startsWith(href)) {
                        return {
                            category: link.textContent.trim(),
                            href: href
                        };
                    }
                }
            }
            
            // Fallback to breadcrumbs
            const breadcrumbs = document.querySelectorAll('.breadcrumb-item');
            if (breadcrumbs.length) {
                // Get the last non-active breadcrumb which should be the parent category
                const lastBreadcrumb = Array.from(breadcrumbs).pop();
                if (lastBreadcrumb) {
                    return {
                        category: lastBreadcrumb.getAttribute('title'),
                        href: lastBreadcrumb.getAttribute('href')
                    };
                }
            }
            
            return null;
        }
        """
        category_info = await page.evaluate(category_script)
        
        # Download current page while we look for more links
        parsed_url = urlparse(base_url)
        relative_path = parsed_url.path.lstrip('/')
        filepath = os.path.join(OUTPUT_DIR, relative_path)
        if not filepath.endswith('.md'):
            filepath += '.md'
            
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Download current page if needed
        if force_download or not os.path.exists(filepath):
            content, title = await extract_content(page, base_url, session, manager)
            if content and title:
                # Add category to frontmatter if available
                if category_info:
                    content = f"""---
title: {title}
category: {category_info['category']}
category_url: {category_info['href']}
---

{content}"""
                else:
                    content = f"""---
title: {title}
---

{content}"""
                
                # Save the file using markdown processor
                filepath = manager.markdown_processor.save_content(base_url, content, title)
                print(f"Downloaded: {filepath}")
        
        # Update link filtering based on selected documentation type
        doc_type = parsed_url.path.split('/')[4]  # Extract doc type from URL
        link_filter = f"""
        Array.from(document.getElementsByTagName('a'))
            .map(a => a.href)
            .filter(href => 
                href.includes('/documentation/en-us/{doc_type}') &&
                !href.includes('#') &&  // Exclude anchor links
                !href.endsWith('.png') &&  // Exclude image links
                !href.endsWith('.jpg')
            )
        """
        
        hrefs = await page.evaluate(link_filter)
        
        all_links = set(hrefs)
        child_links = set()
        
        # Process child pages
        for href in hrefs:
            if href not in processed_urls:
                child_links.update(await get_links_and_download(
                    page, session, manager, href, processed_urls, force_download
                ))
        
        return list(all_links | child_links)
        
    except RecursionError as e:
        manager.recursion_errors[base_url] = DownloadError(
            url=base_url,
            error_type="RecursionError",
            message=str(e)
        )
        logging.error(f"Recursion error processing {base_url}: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"Error processing {base_url}: {str(e)}")
        return []

class WebMarkScraper:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.browser = None
        self.session = None
        self.manager = DownloadManager()
        
    async def initialize(self):
        """Initialize browser and session"""
        self.session = aiohttp.ClientSession()
        try:
            print("Starting browser...")
            self.browser = await uc.start(
                headless=self.config.get_setting("headless"),
                lang=self.config.get_setting("browser_lang")
            )
            return True
        except Exception as e:
            logging.error(f"Failed to start browser: {e}")
            return False
            
    async def cleanup(self):
        """Cleanup resources"""
        if self.browser:
            try:
                await self.browser.stop()
            except Exception as e:
                logging.error(f"Error stopping browser: {e}")
        
        if self.session and not self.session.closed:
            try:
                await self.session.close()
            except Exception as e:
                logging.error(f"Error closing session: {e}")

async def main(*, force_download=False, download_images=True, base_url=None, config_manager=None):
    """Main entry point for the scraper
    
    Args:
        force_download (bool): Force redownload of existing files
        download_images (bool): Download images along with content
        base_url (str, optional): Override default base URL
        config_manager (ConfigManager, optional): Configuration manager instance
    """
    start_time = time.time()
    
    # Use provided config_manager or create new one
    config = config_manager or ConfigManager()
    
    # Initialize scraper with configuration
    scraper = WebMarkScraper(config)
    
    try:
        # Initialize browser and session
        if not await scraper.initialize():
            raise Exception("Failed to initialize scraper")
        
        # Get output directory from config
        output_dir = config.get_setting("output_dir")
        os.makedirs(output_dir, exist_ok=True)
        
        # Use provided base_url or get from config based on selected preset
        scraper_url = base_url or config.get_setting("base_url")
        if not scraper_url:
            raise Exception("No base URL provided")
            
        print("Getting initial page...")
        page = await scraper.browser.get(scraper_url)
        
        if not page:
            raise Exception("Failed to get initial page")
            
        print("Getting links and downloading content...")
        links = await get_links_and_download(
            page, 
            scraper.session, 
            scraper.manager,
            base_url=scraper_url,
            force_download=force_download
        )
        print(f"Processed {len(links)} pages.")
        
        # After initial downloads complete, try to retry failed ones
        await scraper.manager.retry_failed_downloads(scraper.session, page)
        
        # Post-process downloads to add/verify chapter metadata
        await scraper.manager.post_process_downloads(scraper.session, page)
        
    except Exception as e:
        print(f"An error occurred in main: {str(e)}")
        logging.error(f"Scraping error: {str(e)}")
    finally:
        await scraper.cleanup()
        if scraper.session and not scraper.session.closed:
            await scraper.session.close()
        print(f"\nAll pages saved to {output_dir}")

    # Format documentation after processing
    formatter = BookFormatter(output_dir)
    formatter.format_documentation()
    
    # Generate navigation and print versions using DocumentProcessor
    doc_processor = DocumentProcessor(output_dir)
    doc_processor.generate_combined_book()
    
    # Generate basic index and print version through DownloadManager
    scraper.manager.generate_index()
    scraper.manager.generate_print_ready_version()
    
    # Print statistics
    elapsed_time = time.time() - start_time
    avg_download_time = sum(scraper.manager.download_times) / len(scraper.manager.download_times) if scraper.manager.download_times else 0
    print(f"\nScraping completed in {elapsed_time:.2f} seconds")
    print(f"Average download time: {avg_download_time:.2f} seconds")
    print(f"Pages processed: {len(scraper.manager.processed_urls)}")
    print(f"Failed downloads: {len(scraper.manager.failed_urls)}")

if __name__ == "__main__":
    try:
        asyncio.run(main(force_download=False, download_images=True))
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
