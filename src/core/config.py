#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Configuration management
"""

import json
import logging
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager for the application"""
    
    def __init__(self):
        """Initialize the configuration manager"""
        # Define the configuration directory and file
        self.config_dir = Path.home() / '.universal_debugger'
        self.config_file = self.config_dir / 'config.json'
        
        # Create the configuration directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)
        
        # Default configuration
        self.default_config = {
            "ui": {
                "theme": "light",
                "font_size": 10,
                "window_size": [1024, 768],
                "window_position": [100, 100],
                "window_maximized": False
            },
            "serial": {
                "default_baud_rate": 115200,
                "default_data_bits": 8,
                "default_parity": "N",
                "default_stop_bits": 1,
                "default_flow_control": "none",
                "auto_reconnect": True,
                "reconnect_interval": 5
            },
            "devices": {
                "auto_connect": True,
                "scan_interval": 2,
                "preferred_devices": []
            },
            "logging": {
                "log_to_file": True,
                "log_level": "INFO",
                "max_log_size": 10485760,  # 10 MB
                "max_log_files": 5
            },
            "visualization": {
                "update_interval": 100,  # ms
                "max_data_points": 1000,
                "default_chart_type": "line"
            },
            "scripting": {
                "script_directory": str(self.config_dir / "scripts"),
                "auto_save_scripts": True,
                "python_path": "",  # Use system Python by default
                "allowed_modules": ["time", "math", "random", "datetime", "json", "re"]
            }
        }
        
        # Load the configuration
        self.config = self.load()
    
    def load(self):
        """Load the configuration from the file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_file}")
                
                # Merge with default config to ensure all keys exist
                return self._merge_configs(self.default_config, config)
            else:
                logger.info("Configuration file not found, using defaults")
                return self.default_config.copy()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return self.default_config.copy()
    
    def save(self):
        """Save the configuration to the file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def get(self, section, key, default=None):
        """Get a configuration value"""
        try:
            return self.config[section][key]
        except KeyError:
            if default is not None:
                return default
            try:
                return self.default_config[section][key]
            except KeyError:
                logger.warning(f"Configuration key not found: {section}.{key}")
                return None
    
    def set(self, section, key, value):
        """Set a configuration value"""
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
        logger.debug(f"Configuration updated: {section}.{key} = {value}")
    
    def _merge_configs(self, default, user):
        """Recursively merge user config with default config"""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def reset_to_defaults(self):
        """Reset the configuration to default values"""
        self.config = self.default_config.copy()
        logger.info("Configuration reset to defaults")
        return self.save()
    
    def get_section(self, section):
        """Get an entire configuration section"""
        try:
            return self.config[section]
        except KeyError:
            logger.warning(f"Configuration section not found: {section}")
            try:
                return self.default_config[section]
            except KeyError:
                return {}