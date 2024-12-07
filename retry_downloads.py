import asyncio
import argparse
import json
import aiohttp
from pathlib import Path
from webmark_uefn import DownloadManager, uc

async def retry_downloads(urls: list = None, force_recursion: bool = False):
    """Retry downloading specific URLs or all failed downloads"""
    output_dir = "./downloaded_docs"
    manager = DownloadManager(output_dir)
    
    # If no URLs provided, load from recursion_errors.json
    if not urls:
        error_file = Path(output_dir) / 'recursion_errors.json'
        if error_file.exists():
            with open(error_file) as f:
                errors = json.load(f)
                urls = list(errors.keys())
        else:
            print("No failed downloads found to retry.")
            return

    browser = None
    async with aiohttp.ClientSession() as session:
        try:
            print("Starting browser...")
            browser = await uc.start(
                headless=False,
                lang="en-US"
            )
            
            if force_recursion:
                import sys
                original_limit = sys.getrecursionlimit()
                sys.setrecursionlimit(5000)
            
            await manager.retry_specific_urls(urls, session, browser)
            
            if force_recursion:
                sys.setrecursionlimit(original_limit)
                
        finally:
            if browser:
                browser.stop()

def main():
    parser = argparse.ArgumentParser(description='Retry failed downloads')
    parser.add_argument('--urls', nargs='*', help='Specific URLs to retry')
    parser.add_argument('--force-recursion', action='store_true', 
                       help='Increase recursion limit for retry attempts')
    parser.add_argument('--list-failed', action='store_true',
                       help='List all failed downloads')
    args = parser.parse_args()
    
    if args.list_failed:
        output_dir = "./downloaded_docs"
        error_file = Path(output_dir) / 'recursion_errors.json'
        if error_file.exists():
            with open(error_file) as f:
                errors = json.load(f)
                print("\nFailed downloads:")
                for url, error in errors.items():
                    print(f"\nURL: {url}")
                    print(f"Error: {error['error_type']}")
                    print(f"Message: {error['message']}")
        else:
            print("No failed downloads found.")
        return

    asyncio.run(retry_downloads(args.urls, args.force_recursion))

if __name__ == "__main__":
    main() 