from urllib.parse import urlparse
import asyncio
import os
import aiohttp
import time
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
import pickle
from dataclasses import dataclass, asdict, field
import yaml
from markdown_utils import MarkdownProcessor
from markdownify import markdownify as md
from config_manager import ConfigManager
from sitemap import Sitemap
import nodriver as uc

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
    def __init__(self, output_dir: str, progress_callback=None, status_callback=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        
        # Initialize processors
        self.markdown_processor = MarkdownProcessor(output_dir)
        
        # Initialize state
        self.completed_urls = set()
        self.failed_downloads = {}
        self.retry_queue = []
        self.recursion_errors = {}
        self.status_map = {}
        self.should_stop = False
        self.browser = None
        self.is_shutting_down = False
        
        # Load existing state
        self._load_state()
        
    def _load_state(self):
        """Load download state from file"""
        state_file = Path(self.output_dir) / '.download_state'
        if state_file.exists():
            with open(state_file, 'rb') as f:
                data = pickle.load(f)
                self.completed_urls = set(data['completed_urls'])
                self.failed_downloads = dict(data['failed_downloads'])
                self.retry_queue = list(data['retry_queue'])
                self.recursion_errors = dict(data['recursion_errors'])
                self.status_map = dict(data['status_map'])
                self.should_stop = data['should_stop']
                self.browser = data['browser']

    def set_callbacks(self, progress_callback=None, status_callback=None):
        """Set callbacks for UI updates"""
        self.progress_callback = progress_callback
        self.status_callback = status_callback

    async def initialize_browser(self):
        """Initialize browser with proper settings"""
        try:
            options = {
                'headless': True,
                'locale': 'en-US',
                'timeout': 30000
            }
            browser = await uc.start(**options)
            return browser
        except Exception as e:
            logging.error(f"Browser initialization error: {str(e)}")
            return None

    async def process_url(self, url: str, session, force_download=False, download_images=True):
        """Process a single URL with status code handling"""
        if url in self.completed_urls and not force_download:
            return True
            
        try:
            if self.status_callback:
                self.status_callback(f"Processing {url}")
                
            async with session.get(url) as response:
                status_code = response.status
                
                if status_code != 200:
                    error_msg = f"HTTP {status_code}"
                    self.failed_downloads[url] = (status_code, error_msg)
                    self.retry_queue.append(url)
                    self.status_map[url] = {
                        'status_code': status_code,
                        'error_message': error_msg,
                        'timestamp': datetime.now().isoformat()
                    }
                    return False
                    
                content = await response.text()
                await self.process_page(url, content, session, download_images)
                self.completed_urls.add(url)
                
                if self.progress_callback:
                    progress = (len(self.completed_urls) / (len(self.completed_urls) + len(self.failed_downloads))) * 100
                    self.progress_callback(progress)
                    
                return True
                
        except Exception as e:
            error_msg = str(e)
            self.failed_downloads[url] = (0, error_msg)
            self.retry_queue.append(url)
            self.status_map[url] = {
                'status_code': 0,
                'error_message': error_msg,
                'timestamp': datetime.now().isoformat()
            }
            return False

    async def retry_specific_urls(self, urls: list, session, browser=None):
        """Retry downloading specific URLs with recursion handling"""
        if not browser and not await self.initialize_browser():
            raise Exception("Failed to initialize browser")
            
        browser_to_use = browser or self.browser
        
        for url in urls:
            logging.info(f"Retrying download for: {url}")
            try:
                if url in self.recursion_errors:
                    # Handle recursion errors differently
                    import sys
                    original_limit = sys.getrecursionlimit()
                    sys.setrecursionlimit(5000)
                    try:
                        await self.process_url(url, session, force_download=True)
                        if url in self.completed_urls:
                            del self.recursion_errors[url]
                    finally:
                        sys.setrecursionlimit(original_limit)
                else:
                    # Normal retry
                    await self.process_url(url, session, force_download=True)
                    
            except Exception as e:
                logging.error(f"Still failed to download {url}: {str(e)}")

    async def download_with_retry(self, session, url: str, **kwargs):
        """Download with retry logic and status code handling"""
        retries = 0
        while retries < self.max_retries and not self.should_stop:
            try:
                success = await self.process_url(url, session, **kwargs)
                if success:
                    return True, None
                    
                status_code = self.failed_downloads.get(url, (0, ''))[0]
                if status_code in [429, 503, 504]:  # Rate limit or server errors
                    retries += 1
                    if retries < self.max_retries:
                        await asyncio.sleep(self.retry_delay * retries)  # Exponential backoff
                        continue
                        
                return False, self.failed_downloads.get(url)
                
            except Exception as e:
                retries += 1
                if retries < self.max_retries:
                    await asyncio.sleep(self.retry_delay * retries)
                    continue
                    
                return False, (0, str(e))
                
        return False, self.failed_downloads.get(url)

    async def cleanup(self):
        """Cleanup resources with lock protection"""
        async with self._cleanup_lock:
            self.should_stop = True
            if self.browser:
                try:
                    browser = self.browser
                    self.browser = None
                    await browser.stop()
                except Exception as e:
                    logging.error(f"Error stopping browser: {str(e)}")
            
            self.save_failed_downloads(self.output_dir)
            self.save_status()

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
    async def retry_failed_downloads(self, session, page, force_recursion=False):
        """Retry failed downloads with UI feedback"""
        if not self.recursion_errors and not self.failed_downloads:
            if self.status_callback:
                self.status_callback("No failed downloads found")
            return
            
        total_retries = len(self.recursion_errors) + len(self.failed_downloads)
        if self.status_callback:
            self.status_callback(f"Retrying {total_retries} failed downloads...")
        
        if force_recursion:
            import sys
            original_limit = sys.getrecursionlimit()
            sys.setrecursionlimit(5000)
        
        try:
            # Process recursion errors
            for i, (url, error) in enumerate(list(self.recursion_errors.items())):
                if self.should_stop:
                    break
                    
                if self.progress_callback:
                    self.progress_callback(i / total_retries * 100)
                    
                try:
                    await self.process_url(url, session, force_download=True)
                    del self.recursion_errors[url]
                except Exception as e:
                    logging.error(f"Still failed to download {url}: {str(e)}")
            
            # Process other failed downloads
            for i, (url, _) in enumerate(list(self.failed_downloads.items())):
                if self.should_stop:
                    break
                    
                if self.progress_callback:
                    self.progress_callback((i + len(self.recursion_errors)) / total_retries * 100)
                    
                await self.download_with_retry(session, url, force_download=True)
                
        finally:
            if force_recursion:
                sys.setrecursionlimit(original_limit)
            self.save_state()
            self.save_failed_downloads(self.output_dir)
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
    """Extract content and links from page"""
    try:
        # Wait for content to load
        await asyncio.sleep(1)
        
        # Get page content
        content = await page.content()
        if not content:
            return None, None, []
            
        # Extract title and links
        title = await page.title()
        links = await page.links()
        
        # Filter and process links
        valid_links = []
        for link in links:
            href = await link.get_attribute('href')
            if href and isinstance(href, str):
                if href.startswith('/documentation/'):
                    href = f"https://dev.epicgames.com{href}"
                if href.startswith('https://dev.epicgames.com/documentation/'):
                    valid_links.append(href)
        
        # Process content
        md_content = md(content)
        
        return md_content, title, valid_links
        
    except Exception as e:
        logging.error(f"Error extracting content from {url}: {str(e)}")
        return None, None, []

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
        
        # Extract category information
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
        
        # Download current page
        parsed_url = urlparse(base_url)
        relative_path = parsed_url.path.lstrip('/')
        filepath = os.path.join(manager.output_dir, relative_path)
        if not filepath.endswith('.md'):
            filepath += '.md'
            
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        if force_download or not os.path.exists(filepath):
            content, title = await extract_content(page, base_url, session, manager)
            if content and title:
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