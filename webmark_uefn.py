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

from typing import Optional, List, Set

# from dataclasses import dataclass, asdict, field

from combine_docs import DocumentProcessor
from book_formatter import BookFormatter
from markdown_utils import MarkdownProcessor
from markdownify import markdownify as md
from config_manager import ConfigManager
from image_processor import ImageProcessor
from download_manager import DownloadManager, DownloadState, DownloadStatus, DownloadError, get_links_and_download


# At the top of the file, after imports
__all__ = ['WebMarkScraper', 'main']

# Remove the module-level config
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

class WebMarkScraper:
    def __init__(self, config_manager=None, progress_callback=None, status_callback=None):
        self.config_manager = config_manager or ConfigManager()
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        
        # Initialize paths
        self.output_dir = self.config_manager.get_setting("output_dir")
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.manager = DownloadManager(output_dir=self.output_dir)
        self.session = None
        self.browser = None
        self._initialized = False
        self._cleanup_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize browser and session"""
        if self._initialized:
            return True
            
        try:
            # Create session
            self.session = aiohttp.ClientSession()
            
            # Initialize browser with config settings
            browser_options = {}
            headless = self.config_manager.get_setting("headless", True)
            if headless is not None:
                browser_options['headless'] = headless

            lang = self.config_manager.get_setting("browser_lang", 'en-US')
            if lang:
                browser_options['lang'] = lang

            # Start browser
            self.browser = await uc.start(**browser_options)
            
            if not self.browser:
                raise Exception("Failed to start browser")
                
            self._initialized = True
            return True
            
        except Exception as e:
            logging.exception("Failed to initialize scraper")
            if self.status_callback:
                self.status_callback(f"Initialization error: {str(e)}")
            return False
            
    async def main(self, base_url: str, force_download: bool = False, download_images: bool = True) -> bool:
        """Main scraping function"""
        try:
            if not await self.initialize():
                return False
                
            # Process URL
            await self.manager.process_url(
                base_url, 
                self.session,
                force_download=force_download,
                download_images=download_images
            )
            
            # Generate index
            self.manager.generate_index()
            
            return True
            
        except Exception as e:
            logging.error(f"Error in main scraping: {str(e)}")
            return False
            
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources such as the browser and session."""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self.session:
                await self.session.close()
                self.session = None
            logging.info("Scraper cleanup completed successfully.")
        except Exception as e:
            logging.error(f"Error during scraper cleanup: {e}")

    async def scrape(self, base_url: str, force_download: bool = False, download_images: bool = True) -> bool:
        """Wrapper for the main scraping function."""
        return await self.main(base_url, force_download, download_images)

async def main(*, force_download=False, download_images=True, base_url=None, config_manager=None):
    """Main entry point for the scraper"""
    try:
        scraper = WebMarkScraper(config_manager=config_manager)
        
        if not base_url:
            raise ValueError("Base URL is required")
            
        return await scraper.main(
            base_url=base_url,
            force_download=force_download,
            download_images=download_images
        )
        
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        asyncio.run(main(force_download=False, download_images=True))
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")