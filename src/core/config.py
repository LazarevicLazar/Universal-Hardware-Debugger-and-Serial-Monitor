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
import threading
from typing import Any, Dict, List, Union, Optional, Tuple

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager for the application with schema validation"""
    
    def __init__(self):
        """Initialize the configuration manager"""
        # Define the configuration directory and file
        self.config_dir = Path.home() / '.universal_debugger'
        self.config_file = self.config_dir / 'config.json'
        
        # Create the configuration directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)
        
        # Thread safety
        self.config_lock = threading.RLock()
        
        # Define the configuration schema
        self.schema = {
            "ui": {
                "theme": {"type": "string", "enum": ["light", "dark"], "default": "light"},
                "font_size": {"type": "integer", "min": 8, "max": 24, "default": 10},
                "window_size": {"type": "array", "items": {"type": "integer", "min": 100}, "default": [1024, 768]},
                "window_position": {"type": "array", "items": {"type": "integer"}, "default": [100, 100]},
                "window_maximized": {"type": "boolean", "default": False}
            },
            "serial": {
                "default_baud_rate": {"type": "integer", "enum": [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600], "default": 115200},
                "default_data_bits": {"type": "integer", "enum": [5, 6, 7, 8], "default": 8},
                "default_parity": {"type": "string", "enum": ["N", "E", "O", "M", "S"], "default": "N"},
                "default_stop_bits": {"type": "number", "enum": [1, 1.5, 2], "default": 1},
                "default_flow_control": {"type": "string", "enum": ["none", "xonxoff", "rtscts", "dsrdtr"], "default": "none"},
                "auto_reconnect": {"type": "boolean", "default": True},
                "reconnect_interval": {"type": "integer", "min": 1, "max": 60, "default": 5},
                "max_buffer_size": {"type": "integer", "min": 1024, "max": 10485760, "default": 1048576},  # 1MB
                "stalled_timeout": {"type": "integer", "min": 5, "max": 300, "default": 30}  # seconds
            },
            "devices": {
                "auto_connect": {"type": "boolean", "default": True},
                "scan_interval": {"type": "integer", "min": 1, "max": 60, "default": 2},
                "preferred_devices": {"type": "array", "items": {"type": "string"}, "default": []},
                "connection_timeout": {"type": "integer", "min": 1, "max": 30, "default": 5},
                "max_reconnect_attempts": {"type": "integer", "min": 1, "max": 10, "default": 5}
            },
            "logging": {
                "log_to_file": {"type": "boolean", "default": True},
                "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], "default": "INFO"},
                "max_log_size": {"type": "integer", "min": 1048576, "max": 104857600, "default": 10485760},  # 10 MB
                "max_log_files": {"type": "integer", "min": 1, "max": 20, "default": 5},
                "log_format": {"type": "string", "default": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
            },
            "visualization": {
                "update_interval": {"type": "integer", "min": 50, "max": 5000, "default": 100},  # ms
                "max_data_points": {"type": "integer", "min": 100, "max": 100000, "default": 1000},
                "default_chart_type": {"type": "string", "enum": ["line", "bar", "gauge"], "default": "line"},
                "auto_scale": {"type": "boolean", "default": True},
                "default_color": {"type": "string", "default": "#0000FF"}
            },
            "scripting": {
                "script_directory": {"type": "string", "default": str(self.config_dir / "scripts")},
                "auto_save_scripts": {"type": "boolean", "default": True},
                "python_path": {"type": "string", "default": ""},  # Use system Python by default
                "allowed_modules": {"type": "array", "items": {"type": "string"},
                                   "default": ["time", "math", "random", "datetime", "json", "re"]},
                "max_execution_time": {"type": "integer", "min": 1, "max": 300, "default": 60},  # seconds
                "max_memory_usage": {"type": "integer", "min": 1048576, "max": 1073741824, "default": 104857600}  # 100 MB
            }
        }
        
        # Generate default configuration from schema
        self.default_config = self._generate_default_config()
        
        # Load the configuration
        self.config = self.load()
        
        # Validate the configuration
        self.validate()
    
    def _generate_default_config(self) -> Dict[str, Any]:
        """Generate default configuration from schema"""
        default_config = {}
        
        for section, section_schema in self.schema.items():
            default_config[section] = {}
            for key, key_schema in section_schema.items():
                default_config[section][key] = key_schema["default"]
                
        return default_config
    
    def load(self) -> Dict[str, Any]:
        """Load the configuration from the file with thread safety"""
        with self.config_lock:
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
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing configuration file: {e}")
                logger.info("Using default configuration due to parsing error")
                return self.default_config.copy()
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
                return self.default_config.copy()
    
    def save(self) -> bool:
        """Save the configuration to the file with thread safety"""
        with self.config_lock:
            try:
                # Validate before saving
                self.validate()
                
                # Create a backup of the existing config file if it exists
                if self.config_file.exists():
                    backup_file = self.config_file.with_suffix('.json.bak')
                    try:
                        shutil.copy2(self.config_file, backup_file)
                        logger.debug(f"Created backup of configuration at {backup_file}")
                    except Exception as e:
                        logger.warning(f"Failed to create backup of configuration: {e}")
                
                with open(self.config_file, 'w') as f:
                    json.dump(self.config, f, indent=4)
                logger.info(f"Configuration saved to {self.config_file}")
                return True
            except Exception as e:
                logger.error(f"Error saving configuration: {e}")
                return False
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value with validation"""
        with self.config_lock:
            # Check if the section and key exist in the schema
            if section not in self.schema:
                logger.warning(f"Configuration section not found in schema: {section}")
                return default
            
            if key not in self.schema[section]:
                logger.warning(f"Configuration key not found in schema: {section}.{key}")
                return default
            
            # Get the value from the config or use default
            try:
                value = self.config[section][key]
            except KeyError:
                # Use the provided default or the schema default
                if default is not None:
                    return default
                return self.schema[section][key]["default"]
            
            # Validate the value against the schema
            schema_entry = self.schema[section][key]
            if not self._validate_value(value, schema_entry):
                logger.warning(f"Invalid configuration value for {section}.{key}: {value}, using default")
                return schema_entry["default"]
            
            return value
    
    def set(self, section: str, key: str, value: Any) -> bool:
        """Set a configuration value with validation"""
        with self.config_lock:
            # Check if the section and key exist in the schema
            if section not in self.schema:
                logger.warning(f"Cannot set value: section '{section}' not in schema")
                return False
            
            if key not in self.schema[section]:
                logger.warning(f"Cannot set value: key '{key}' not in schema for section '{section}'")
                return False
            
            # Validate the value against the schema
            schema_entry = self.schema[section][key]
            if not self._validate_value(value, schema_entry):
                logger.warning(f"Cannot set value: '{value}' is invalid for {section}.{key}")
                return False
            
            # Create section if it doesn't exist
            if section not in self.config:
                self.config[section] = {}
            
            # Set the value
            self.config[section][key] = value
            logger.debug(f"Configuration updated: {section}.{key} = {value}")
            return True
    
    def _validate_value(self, value: Any, schema_entry: Dict[str, Any]) -> bool:
        """Validate a value against its schema entry"""
        value_type = schema_entry["type"]
        
        # Check type
        if value_type == "string" and not isinstance(value, str):
            return False
        elif value_type == "integer" and not isinstance(value, int):
            return False
        elif value_type == "number" and not isinstance(value, (int, float)):
            return False
        elif value_type == "boolean" and not isinstance(value, bool):
            return False
        elif value_type == "array" and not isinstance(value, list):
            return False
        
        # Check constraints
        if "enum" in schema_entry and value not in schema_entry["enum"]:
            return False
        
        if "min" in schema_entry:
            if value_type == "array" and len(value) < schema_entry["min"]:
                return False
            elif (value_type == "integer" or value_type == "number") and value < schema_entry["min"]:
                return False
        
        if "max" in schema_entry:
            if value_type == "array" and len(value) > schema_entry["max"]:
                return False
            elif (value_type == "integer" or value_type == "number") and value > schema_entry["max"]:
                return False
        
        # Check array items if specified
        if value_type == "array" and "items" in schema_entry and value:
            item_schema = schema_entry["items"]
            for item in value:
                if not self._validate_value(item, item_schema):
                    return False
        
        return True
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge user config with default config"""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def validate(self) -> bool:
        """Validate the entire configuration against the schema"""
        with self.config_lock:
            valid = True
            fixed_values = 0
            
            # Check each section and key
            for section, section_schema in self.schema.items():
                if section not in self.config:
                    logger.warning(f"Missing section in configuration: {section}")
                    self.config[section] = {}
                    valid = False
                
                for key, key_schema in section_schema.items():
                    # Check if key exists
                    if section not in self.config or key not in self.config[section]:
                        logger.warning(f"Missing key in configuration: {section}.{key}")
                        if section not in self.config:
                            self.config[section] = {}
                        self.config[section][key] = key_schema["default"]
                        fixed_values += 1
                        valid = False
                    else:
                        # Validate the value
                        value = self.config[section][key]
                        if not self._validate_value(value, key_schema):
                            logger.warning(f"Invalid value in configuration: {section}.{key} = {value}")
                            self.config[section][key] = key_schema["default"]
                            fixed_values += 1
                            valid = False
            
            if fixed_values > 0:
                logger.info(f"Fixed {fixed_values} invalid configuration values")
            
            return valid
    
    def reset_to_defaults(self) -> bool:
        """Reset the configuration to default values"""
        with self.config_lock:
            self.config = self.default_config.copy()
            logger.info("Configuration reset to defaults")
            return self.save()
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get an entire configuration section"""
        with self.config_lock:
            if section not in self.schema:
                logger.warning(f"Configuration section not found in schema: {section}")
                return {}
            
            try:
                return self.config[section].copy()
            except KeyError:
                logger.warning(f"Configuration section not found: {section}")
                try:
                    return self.default_config[section].copy()
                except KeyError:
                    return {}
    
    def get_schema(self, section: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
        """Get the schema for a section, key, or the entire schema"""
        with self.config_lock:
            if section is None:
                return self.schema.copy()
            
            if section not in self.schema:
                logger.warning(f"Schema section not found: {section}")
                return {}
            
            if key is None:
                return self.schema[section].copy()
            
            if key not in self.schema[section]:
                logger.warning(f"Schema key not found: {section}.{key}")
                return {}
            
            return self.schema[section][key].copy()
    
    def import_config(self, config_file: str) -> bool:
        """Import configuration from an external file"""
        try:
            with open(config_file, 'r') as f:
                imported_config = json.load(f)
            
            with self.config_lock:
                # Merge with current config
                self.config = self._merge_configs(self.config, imported_config)
                
                # Validate the merged config
                self.validate()
                
                # Save the configuration
                return self.save()
        except Exception as e:
            logger.error(f"Error importing configuration: {e}")
            return False
    
    def export_config(self, config_file: str) -> bool:
        """Export configuration to an external file"""
        try:
            with self.config_lock:
                with open(config_file, 'w') as f:
                    json.dump(self.config, f, indent=4)
                
                logger.info(f"Configuration exported to {config_file}")
                return True
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return False