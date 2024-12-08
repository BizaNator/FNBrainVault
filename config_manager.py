from pathlib import Path
import json
from typing import Dict, List, Optional
import logging

class ConfigManager:
    def __init__(self, config_file: str = "scraper_config.json"):
        self.config_file = Path(config_file)
        self.default_config = {
            "presets": {
                "documentation": {
                    "UEFN": {
                        "name": "UEFN Documentation",
                        "base_url": "https://dev.epicgames.com/documentation/en-us/uefn/unreal-editor-for-fortnite-documentation",
                        "link_pattern": "/documentation/en-us/uefn",
                        "description": "Unreal Editor for Fortnite Documentation"
                    },
                    "Fortnite Creative": {
                        "name": "Fortnite Creative",
                        "base_url": "https://dev.epicgames.com/documentation/en-us/fortnite-creative/fortnite-creative-documentation",
                        "link_pattern": "/documentation/en-us/fortnite-creative",
                        "description": "Fortnite Creative Documentation"
                    },
                    "Verse": {
                        "name": "Verse Programming",
                        "base_url": "https://dev.epicgames.com/documentation/en-us/uefn/learn-programming-with-verse-in-unreal-editor-for-fortnite",
                        "link_pattern": "/documentation/en-us/uefn",
                        "description": "Verse Programming Language Documentation"
                    },
                    "VerseAPI": {
                        "name": "Verse API",
                        "base_url": "https://dev.epicgames.com/documentation/en-us/uefn/verse-api",
                        "link_pattern": "/documentation/en-us/uefn/verse-api",
                        "description": "Verse API Reference"
                    },
                    "Unreal Engine": {
                        "name": "Unreal Engine",
                        "base_url": "https://dev.epicgames.com/documentation/en-us/unreal-engine",
                        "link_pattern": "/documentation/en-us/unreal-engine",
                        "description": "Unreal Engine Documentation"
                    },
                    "MetaHuman": {
                        "name": "MetaHuman",
                        "base_url": "https://dev.epicgames.com/documentation/en-us/metahuman",
                        "link_pattern": "/documentation/en-us/metahuman",
                        "description": "MetaHuman Documentation"
                    },
                    "Twinmotion": {
                        "name": "Twinmotion",
                        "base_url": "https://dev.epicgames.com/documentation/en-us/twinmotion",
                        "link_pattern": "/documentation/en-us/twinmotion",
                        "description": "Twinmotion Documentation"
                    },
                    "RealityScan": {
                        "name": "RealityScan",
                        "base_url": "https://dev.epicgames.com/documentation/en-us/reality-scan",
                        "link_pattern": "/documentation/en-us/reality-scan",
                        "description": "RealityScan Documentation"
                    },
                    "Fab": {
                        "name": "Fab",
                        "base_url": "https://dev.epicgames.com/documentation/en-us/fab",
                        "link_pattern": "/documentation/en-us/fab",
                        "description": "Fab Documentation"
                    }
                }
            },
            "settings": {
                "output_dir": "./downloaded_docs",
                "images_dir": "./downloaded_docs/images",
                "max_concurrent": 5,
                "rate_limit_delay": 0.5,
                "log_file": "webmark_uefn.log",
                "headless": False,
                "browser_lang": "en-US",
                "retry_attempts": 3,
                "timeout": 30,
                "max_recursion_retries": 2
            }
        }
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Load configuration from file or return defaults"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading config: {e}")
                return self.default_config
        return self.default_config
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def add_preset(self, category: str, name: str, base_url: str, 
                  link_pattern: str, description: str) -> None:
        """Add a new preset to the configuration"""
        if category not in self.config["presets"]:
            self.config["presets"][category] = {}
        
        self.config["presets"][category][name] = {
            "name": name,
            "base_url": base_url,
            "link_pattern": link_pattern,
            "description": description
        }
        self.save_config()
    
    def get_presets(self, category: str) -> Dict:
        """Get all presets for a category"""
        return self.config["presets"].get(category, {})
    
    def get_setting(self, key: str) -> any:
        """Get a setting value"""
        return self.config["settings"].get(key)
    
    def update_setting(self, key: str, value: any) -> None:
        """Update a setting value"""
        self.config["settings"][key] = value
        self.save_config() 