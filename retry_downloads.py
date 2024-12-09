import asyncio
import argparse
import json
import aiohttp
import nodriver as uc
from pathlib import Path
from download_manager import DownloadManager
from config_manager import ConfigManager
import logging

async def retry_downloads(urls: list = None, force_recursion: bool = False, resume: bool = False):
    """Retry downloading specific URLs or resume interrupted downloads"""
    config = ConfigManager()
    output_dir = config.get_setting("output_dir")
    manager = DownloadManager(output_dir)
    
    # If resuming, load from download state
    if resume:
        state_file = Path(output_dir) / '.download_state'
        if state_file.exists():
            state = manager.load_state()
            if state and state.retry_queue:
                urls = state.retry_queue
                print(f"Resuming {len(urls)} interrupted downloads...")
            else:
                print("No interrupted downloads found to resume.")
                return
    # If no URLs provided, check different error files
    elif not urls:
        error_files = {
            'recursion': Path(output_dir) / 'recursion_errors.json',
            'failed': Path(output_dir) / 'failed_downloads.json'
        }
        
        urls = []
        for error_type, file_path in error_files.items():
            if file_path.exists():
                with open(file_path) as f:
                    errors = json.load(f)
                    if error_type == 'recursion':
                        urls.extend(list(errors.keys()))
                    else:
                        urls.extend([url for url, (status, _) in errors.items()])
        
        if not urls:
            print("No failed downloads found to retry.")
            return
        
        print(f"Found {len(urls)} failed downloads to retry.")

    browser = None
    async with aiohttp.ClientSession() as session:
        try:
            print("Starting browser...")
            browser = await uc.start(
                headless=config.get_setting("headless"),
                lang=config.get_setting("browser_lang"),
                timeout=30000,
                options={
                    'no_sandbox': True,
                    'disable_gpu': True,
                    'window_size': (1920, 1080)
                }
            )
            
            if force_recursion:
                import sys
                original_limit = sys.getrecursionlimit()
                sys.setrecursionlimit(5000)
            
            # Process URLs with progress tracking
            total = len(urls)
            for i, url in enumerate(urls, 1):
                print(f"\nProcessing {i}/{total}: {url}")
                try:
                    await manager.process_url(url, session, force_download=True)
                    if url in manager.completed_urls:
                        print(f"Successfully downloaded: {url}")
                    else:
                        print(f"Failed to download: {url}")
                except Exception as e:
                    print(f"Error processing {url}: {str(e)}")
                
                # Save state periodically
                if i % 5 == 0:
                    manager.save_state()
            
            if force_recursion:
                sys.setrecursionlimit(original_limit)
                
        except Exception as e:
            logging.error(f"Error during retry process: {str(e)}")
        finally:
            if browser:
                await browser.stop()
            manager.save_state()
            manager.save_status()

def main():
    parser = argparse.ArgumentParser(description='Retry failed downloads or resume interrupted downloads')
    parser.add_argument('--urls', nargs='*', help='Specific URLs to retry')
    parser.add_argument('--force-recursion', action='store_true', 
                       help='Increase recursion limit for retry attempts')
    parser.add_argument('--resume', action='store_true',
                       help='Resume interrupted downloads')
    parser.add_argument('--list-failed', action='store_true',
                       help='List all failed downloads')
    args = parser.parse_args()
    
    config = ConfigManager()
    output_dir = config.get_setting("output_dir")
    
    if args.list_failed:
        # List both recursion errors and failed downloads
        error_files = {
            'Recursion Errors': Path(output_dir) / 'recursion_errors.json',
            'Failed Downloads': Path(output_dir) / 'failed_downloads.json'
        }
        
        found_errors = False
        for error_type, file_path in error_files.items():
            if file_path.exists():
                with open(file_path) as f:
                    errors = json.load(f)
                    if errors:
                        found_errors = True
                        print(f"\n{error_type}:")
                        for url, error in errors.items():
                            print(f"\nURL: {url}")
                            if isinstance(error, dict):
                                print(f"Error: {error.get('error_type', 'Unknown')}")
                                print(f"Message: {error.get('message', 'No message')}")
                            else:
                                status, msg = error
                                print(f"Status: {status}")
                                print(f"Message: {msg}")
                                
        if not found_errors:
            print("No failed downloads found.")
        return

    asyncio.run(retry_downloads(args.urls, args.force_recursion, args.resume))

if __name__ == "__main__":
    main() 