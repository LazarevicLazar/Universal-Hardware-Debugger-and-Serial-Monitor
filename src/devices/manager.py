#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Device management module
"""

import logging
import platform
import time
from pathlib import Path
import json
import re
import threading
import collections
from typing import Dict, List, Optional, Any, Tuple

import serial
import serial.tools.list_ports
import usb.core
import usb.util

logger = logging.getLogger(__name__)

class DeviceManager:
    """Manages detection and connection of microcontroller devices"""
    
    # Common USB VID:PID pairs for popular microcontrollers
    KNOWN_DEVICES = {
        # Arduino
        "2341:0043": {"name": "Arduino Uno", "type": "arduino"},
        "2341:0001": {"name": "Arduino Mega", "type": "arduino"},
        "2341:0036": {"name": "Arduino Leonardo", "type": "arduino"},
        "2341:8036": {"name": "Arduino Leonardo Bootloader", "type": "arduino"},
        "2341:0010": {"name": "Arduino Mega 2560", "type": "arduino"},
        "2341:8036": {"name": "Arduino Leonardo", "type": "arduino"},
        "2A03:0043": {"name": "Arduino Uno", "type": "arduino"},
        "2A03:0001": {"name": "Arduino Mega", "type": "arduino"},
        
        # ESP32
        "10C4:EA60": {"name": "ESP32 (Silicon Labs CP210x)", "type": "esp32"},
        "1A86:7523": {"name": "ESP32 (CH340)", "type": "esp32"},
        
        # Raspberry Pi Pico
        "2E8A:0005": {"name": "Raspberry Pi Pico", "type": "pico"},
        "2E8A:000A": {"name": "Raspberry Pi Pico W", "type": "pico"},
        
        # STM32
        "0483:5740": {"name": "STM32 Virtual COM Port", "type": "stm32"},
        "0483:DF11": {"name": "STM32 DFU Mode", "type": "stm32"},
        
        # Teensy
        "16C0:0483": {"name": "Teensy", "type": "teensy"},
        "16C0:0478": {"name": "Teensy Serial", "type": "teensy"},
        
        # Particle
        "2B04:C006": {"name": "Particle Photon", "type": "particle"},
        "2B04:C008": {"name": "Particle P1", "type": "particle"},
        "2B04:D006": {"name": "Particle Electron", "type": "particle"},
        
        # Nordic nRF
        "1915:521F": {"name": "Nordic nRF52 DFU", "type": "nordic"},
        "1915:520F": {"name": "Nordic nRF52 USB CDC", "type": "nordic"},
    }
    
    # Common description patterns for device identification
    DESCRIPTION_PATTERNS = {
        r"Arduino": {"name": "Arduino Device", "type": "arduino"},
        r"CH340": {"name": "Serial Converter CH340", "type": "serial"},
        r"FTDI": {"name": "FTDI Serial Adapter", "type": "serial"},
        r"CP210": {"name": "Silicon Labs CP210x", "type": "serial"},
        r"USB Serial": {"name": "USB Serial Device", "type": "serial"},
        r"CDC": {"name": "USB CDC Device", "type": "serial"},
        r"Bluetooth": {"name": "Bluetooth Serial Port", "type": "bluetooth"},
    }
    
    # Hardware ID patterns for device identification
    HWID_PATTERNS = {
        r"VID:PID=2341": {"name": "Arduino Device", "type": "arduino"},
        r"VID:PID=1A86": {"name": "CH340 Serial Converter", "type": "serial"},
        r"VID:PID=0403": {"name": "FTDI Serial Device", "type": "serial"},
        r"VID:PID=10C4": {"name": "Silicon Labs Device", "type": "serial"},
    }
    
    def __init__(self, app):
        """Initialize the device manager"""
        self.app = app
        
        # Thread safety
        self.devices_lock = threading.RLock()
        self.db_lock = threading.RLock()
        
        # List of detected devices
        self.devices = []
        
        # Connection history for detecting flaky connections
        self.connection_history = collections.defaultdict(list)
        self.max_history_entries = 10
        
        # Device database path
        self.device_db_path = Path(__file__).parent.parent.parent / 'resources' / 'device_db' / 'devices.json'
        
        # Load extended device database
        self.load_device_database()
        
        # Scan for devices initially
        self.scan_devices()
    
    def load_device_database(self):
        """Load the extended device database from file"""
        try:
            if self.device_db_path.exists():
                with open(self.device_db_path, 'r') as f:
                    custom_devices = json.load(f)
                
                # Merge with known devices
                self.KNOWN_DEVICES.update(custom_devices)
                logger.info(f"Loaded {len(custom_devices)} custom device profiles")
            else:
                # Create the device database directory if it doesn't exist
                self.device_db_path.parent.mkdir(exist_ok=True)
                
                # Save the default database
                with open(self.device_db_path, 'w') as f:
                    json.dump(self.KNOWN_DEVICES, f, indent=4)
                
                logger.info(f"Created default device database at {self.device_db_path}")
        except Exception as e:
            logger.error(f"Error loading device database: {e}")
    
    def scan_devices(self):
        """Scan for connected devices with improved detection"""
        try:
            # Get list of serial ports
            ports = list(serial.tools.list_ports.comports())
            logger.info(f"Found {len(ports)} serial ports")
            
            # Create a list of new devices
            new_devices = []
            
            for port in ports:
                try:
                    # Create a device ID from VID:PID
                    vid_pid = f"{port.vid:04X}:{port.pid:04X}" if port.vid and port.pid else None
                    
                    # Log port details for debugging
                    logger.info(f"Port: {port.device}, Description: {port.description}, VID:PID: {vid_pid}, HWID: {port.hwid}")
                    
                    # Try multiple identification methods
                    device_info = None
                    
                    # Method 1: VID:PID lookup
                    if vid_pid:
                        with self.db_lock:
                            device_info = self.KNOWN_DEVICES.get(vid_pid, None)
                    
                    # Method 2: Description pattern matching
                    if not device_info and port.description:
                        for pattern, info in self.DESCRIPTION_PATTERNS.items():
                            if re.search(pattern, port.description, re.IGNORECASE):
                                device_info = info
                                break
                    
                    # Method 3: Hardware ID pattern matching
                    if not device_info and port.hwid:
                        for pattern, info in self.HWID_PATTERNS.items():
                            if re.search(pattern, port.hwid, re.IGNORECASE):
                                device_info = info
                                break
                    
                    if device_info:
                        logger.info(f"Recognized as: {device_info['name']} ({device_info['type']})")
                    else:
                        logger.info(f"Unrecognized device")
                    
                    # Create device entry with enhanced metadata
                    device = {
                        "port": port.device,
                        "description": port.description,
                        "hardware_id": port.hwid,
                        "vid_pid": vid_pid,
                        "name": device_info["name"] if device_info else port.description,
                        "type": device_info["type"] if device_info else "unknown",
                        "connected": False,
                        "last_seen": time.time(),
                        "connection_attempts": 0,
                        "connection_failures": 0,
                        "last_connection_time": None,
                        "last_disconnection_time": None,
                        "is_flaky": False
                    }
                    
                    # Add to new devices list
                    new_devices.append(device)
                except Exception as e:
                    logger.error(f"Error processing port {port.device}: {e}")
            
            # Update the devices list with thread safety
            with self.devices_lock:
                self._update_device_list(new_devices)
            
            return self.devices.copy()  # Return a copy to avoid thread safety issues
        except Exception as e:
            logger.error(f"Error scanning for devices: {e}")
            return []
    
    def _update_device_list(self, new_devices):
        """Update the devices list with newly detected devices"""
        # Create a dictionary of current devices by port
        current_devices = {d["port"]: d for d in self.devices}
        
        # Create a dictionary of new devices by port
        new_devices_dict = {d["port"]: d for d in new_devices}
        
        # Update the devices list
        updated_devices = []
        
        # Get configurable timeout from settings
        timeout = self.app.config.get("devices", "connection_timeout", 5)  # seconds
        
        # Add or update devices
        for port, device in new_devices_dict.items():
            if port in current_devices:
                # Update existing device but preserve connection metadata
                current_device = current_devices[port]
                current_device["last_seen"] = time.time()
                
                # Preserve connection metadata
                for key in ["connection_attempts", "connection_failures",
                           "last_connection_time", "last_disconnection_time", "is_flaky"]:
                    if key in current_device:
                        device[key] = current_device[key]
                
                # Preserve connection status
                device["connected"] = current_device["connected"]
                
                updated_devices.append(current_device)
            else:
                # New device
                logger.info(f"New device detected: {device['name']} on {port}")
                
                # Auto-connect if enabled and device is not flagged as flaky
                if (self.app.config.get("devices", "auto_connect", True) and
                    not self._is_device_flaky(port)):
                    self.connect_device(device)
                
                updated_devices.append(device)
        
        # Check for disconnected devices
        current_time = time.time()
        
        for port, device in current_devices.items():
            if port not in new_devices_dict:
                # Device not seen in this scan
                if current_time - device["last_seen"] > timeout:
                    # Device has been gone for too long, consider it disconnected
                    logger.info(f"Device disconnected: {device['name']} on {port}")
                    
                    # Record disconnection time for flaky connection detection
                    device["last_disconnection_time"] = current_time
                    
                    # Update connection history
                    self._update_connection_history(port, "disconnect")
                    
                    # Disconnect if connected
                    if device["connected"]:
                        self.disconnect_device(device)
                        
                    # Check if this device is flaky (frequently connects/disconnects)
                    if self._is_device_flaky(port):
                        device["is_flaky"] = True
                        logger.warning(f"Device {device['name']} on {port} appears to be flaky")
                else:
                    # Device might be temporarily unavailable, keep it in the list
                    updated_devices.append(device)
        
        # Update the devices list
        self.devices = updated_devices
        
        # Notify the UI of changes
        if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'device_panel'):
            self.app.main_window.device_panel.update_device_list()
    
    def connect_device(self, device):
        """Connect to a device with retry logic and connection tracking"""
        try:
            # Check if already connected
            if device["connected"]:
                logger.warning(f"Device already connected: {device['name']} on {device['port']}")
                return True
            
            # Check if device is flaky and auto-connect is disabled for flaky devices
            if device.get("is_flaky", False) and not self.app.config.get("devices", "connect_flaky_devices", False):
                logger.warning(f"Skipping connection to flaky device: {device['name']} on {device['port']}")
                return False
            
            # Increment connection attempts
            device["connection_attempts"] = device.get("connection_attempts", 0) + 1
            
            # Get retry settings from config
            max_retries = self.app.config.get("devices", "max_connection_retries", 3)
            retry_delay = self.app.config.get("devices", "connection_retry_delay", 1.0)  # seconds
            
            # Try to connect with retries
            success = False
            retries = 0
            last_error = None
            
            while retries < max_retries and not success:
                try:
                    # Connect to the device using the serial manager
                    if self.app.serial_manager.open_connection(device["port"]):
                        # Update device status
                        device["connected"] = True
                        device["last_connection_time"] = time.time()
                        
                        # Update connection history
                        self._update_connection_history(device["port"], "connect")
                        
                        logger.info(f"Connected to device: {device['name']} on {device['port']}")
                        
                        # Notify the UI of changes
                        if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'device_panel'):
                            self.app.main_window.device_panel.update_device_list()
                        
                        success = True
                        break
                    else:
                        retries += 1
                        if retries < max_retries:
                            logger.warning(f"Connection attempt {retries} failed for {device['name']} on {device['port']}, retrying...")
                            time.sleep(retry_delay)
                except Exception as e:
                    last_error = e
                    retries += 1
                    if retries < max_retries:
                        logger.warning(f"Connection attempt {retries} failed with error: {e}, retrying...")
                        time.sleep(retry_delay)
            
            if not success:
                # Update failure statistics
                device["connection_failures"] = device.get("connection_failures", 0) + 1
                
                # Log the failure
                if last_error:
                    logger.error(f"Failed to connect to device after {max_retries} attempts: {device['name']} on {device['port']}, error: {last_error}")
                else:
                    logger.error(f"Failed to connect to device after {max_retries} attempts: {device['name']} on {device['port']}")
                
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error connecting to device: {e}")
            return False
    
    def disconnect_device(self, device):
        """Disconnect from a device with proper cleanup"""
        try:
            # Check if connected
            if not device["connected"]:
                logger.warning(f"Device not connected: {device['name']} on {device['port']}")
                return True
            
            # Disconnect from the device using the serial manager
            if self.app.serial_manager.close_connection(device["port"]):
                # Update device status
                device["connected"] = False
                device["last_disconnection_time"] = time.time()
                
                # Update connection history
                self._update_connection_history(device["port"], "disconnect")
                
                logger.info(f"Disconnected from device: {device['name']} on {device['port']}")
                
                # Notify the UI of changes
                if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'device_panel'):
                    self.app.main_window.device_panel.update_device_list()
                
                return True
            else:
                logger.error(f"Failed to disconnect from device: {device['name']} on {device['port']}")
                return False
        except Exception as e:
            logger.error(f"Error disconnecting from device: {e}")
            return False
    
    def get_device_by_port(self, port):
        """Get a device by its port"""
        with self.devices_lock:
            for device in self.devices:
                if device["port"] == port:
                    return device
        return None
    
    def get_device_list(self):
        """Get the list of detected devices"""
        with self.devices_lock:
            # Return a deep copy to prevent thread safety issues
            return [device.copy() for device in self.devices]
    
    def get_connected_devices(self):
        """Get the list of connected devices"""
        with self.devices_lock:
            # Return a deep copy to prevent thread safety issues
            return [device.copy() for device in self.devices if device["connected"]]
    
    def restore_devices(self, devices):
        """Restore device connections from a saved session"""
        if not devices:
            logger.warning("No devices to restore")
            return
            
        logger.info(f"Restoring {len(devices)} device connections")
        
        for saved_device in devices:
            try:
                # Find the device in the current list
                device = self.get_device_by_port(saved_device["port"])
                
                if device and saved_device["connected"]:
                    # Connect to the device
                    logger.info(f"Restoring connection to {device['name']} on {saved_device['port']}")
                    self.connect_device(device)
                elif not device:
                    logger.warning(f"Cannot restore device on port {saved_device['port']}: device not found")
            except Exception as e:
                logger.error(f"Error restoring device {saved_device.get('name', 'unknown')}: {e}")
    
    def add_custom_device(self, vid_pid, name, device_type):
        """Add a custom device to the database"""
        try:
            # Validate inputs
            if not vid_pid or not name or not device_type:
                logger.error("Invalid device information: VID:PID, name, and type are required")
                return False
                
            # Add to the known devices dictionary with thread safety
            with self.db_lock:
                self.KNOWN_DEVICES[vid_pid] = {"name": name, "type": device_type}
                
                # Save the updated database
                try:
                    # Ensure directory exists
                    self.device_db_path.parent.mkdir(exist_ok=True)
                    
                    with open(self.device_db_path, 'w') as f:
                        json.dump(self.KNOWN_DEVICES, f, indent=4)
                except Exception as save_error:
                    logger.error(f"Error saving device database: {save_error}")
                    return False
            
            logger.info(f"Added custom device: {name} ({vid_pid})")
            return True
        except Exception as e:
            logger.error(f"Error adding custom device: {e}")
            return False
            
    def add_manual_port(self, port, device_type="unknown", name=None):
        """Add a manual port that isn't automatically detected"""
        try:
            # Validate port
            if not port:
                logger.error("Invalid port: port name is required")
                return None
                
            # Check if the port already exists
            existing_device = self.get_device_by_port(port)
            if existing_device:
                logger.info(f"Port {port} already exists as {existing_device['name']}")
                return existing_device
            
            # Create a device entry with enhanced metadata
            device = {
                "port": port,
                "description": name or f"Manual {device_type.capitalize()} Device",
                "hardware_id": "MANUAL",
                "vid_pid": None,
                "name": name or f"Manual {device_type.capitalize()} Device on {port}",
                "type": device_type,
                "connected": False,
                "last_seen": time.time(),
                "connection_attempts": 0,
                "connection_failures": 0,
                "last_connection_time": None,
                "last_disconnection_time": None,
                "is_flaky": False,
                "manual": True  # Flag to indicate this is a manually added device
            }
            
            # Add to devices list with thread safety
            with self.devices_lock:
                self.devices.append(device)
                
            logger.info(f"Manually added device: {device['name']} on {port}")
            
            # Notify the UI of changes
            if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'device_panel'):
                self.app.main_window.device_panel.update_device_list()
            
            return device
        except Exception as e:
            logger.error(f"Error adding manual port: {e}")
            return None
            
    def _is_device_flaky(self, port):
        """
        Determine if a device has flaky connections based on connection history
        
        Args:
            port (str): The port of the device
            
        Returns:
            bool: True if the device is considered flaky, False otherwise
        """
        # Get settings from config
        flaky_threshold = self.app.config.get("devices", "flaky_connection_threshold", 0.3)
        history_window = self.app.config.get("devices", "connection_history_window", 10)
        min_attempts = self.app.config.get("devices", "min_connection_attempts", 5)
        
        # Check device-specific history first
        device = self.get_device_by_port(port)
        if device:
            # If device is already marked as flaky, return True
            if device.get("is_flaky", False):
                return True
                
            # Check connection attempts and failures
            attempts = device.get("connection_attempts", 0)
            failures = device.get("connection_failures", 0)
            
            # If we have enough data to make a determination
            if attempts >= min_attempts:
                failure_rate = failures / attempts
                if failure_rate >= flaky_threshold:
                    logger.warning(f"Device {device['name']} on {port} is flaky (failure rate: {failure_rate:.2f})")
                    return True
        
        # Check global connection history
        with self.devices_lock:
            history = self.connection_history.get(port, [])
            
            # If we don't have enough history, it's not flaky
            if len(history) < min_attempts:
                return False
                
            # Get recent history
            recent_history = history[-history_window:]
            
            # Count connection events and disconnection events
            connect_events = sum(1 for event in recent_history if event["action"] == "connect")
            disconnect_events = sum(1 for event in recent_history if event["action"] == "disconnect")
            
            # Calculate time between connect/disconnect events
            if len(recent_history) >= 2:
                # Sort by timestamp
                sorted_events = sorted(recent_history, key=lambda x: x["timestamp"])
                
                # Calculate time differences between events
                time_diffs = []
                for i in range(1, len(sorted_events)):
                    time_diffs.append(sorted_events[i]["timestamp"] - sorted_events[i-1]["timestamp"])
                
                # If we have rapid connect/disconnect cycles, it's flaky
                if time_diffs and len(time_diffs) >= 2:
                    avg_time_diff = sum(time_diffs) / len(time_diffs)
                    min_stable_time = self.app.config.get("devices", "min_stable_connection_time", 30)  # seconds
                    
                    if avg_time_diff < min_stable_time:
                        logger.warning(f"Device on {port} has rapid connect/disconnect cycles (avg {avg_time_diff:.2f}s)")
                        return True
            
            # If there are many more disconnects than connects, it's flaky
            if connect_events > 0 and disconnect_events > 0:
                disconnect_rate = disconnect_events / connect_events
                if disconnect_rate > 1.5:  # More disconnects than connects indicates instability
                    logger.warning(f"Device on {port} has high disconnect rate ({disconnect_rate:.2f})")
                    return True
                    
        return False
        
    def _update_connection_history(self, port, action):
        """
        Update the connection history for a device
        
        Args:
            port (str): The port of the device
            action (str): The action performed ('connect' or 'disconnect')
        """
        # Update device-specific history
        device = self.get_device_by_port(port)
        if device:
            # Initialize history if it doesn't exist
            if "connection_history" not in device:
                device["connection_history"] = []
                
            # Add the event to history
            device["connection_history"].append({
                "action": action,
                "timestamp": time.time(),
                "success": True
            })
            
            # Limit history size to prevent memory growth
            max_history = self.app.config.get("devices", "max_connection_history", 100)
            if len(device["connection_history"]) > max_history:
                device["connection_history"] = device["connection_history"][-max_history:]
        
        # Update global connection history with thread safety
        with self.devices_lock:
            # Add the event to history
            self.connection_history[port].append({
                "action": action,
                "timestamp": time.time(),
                "success": True
            })
            
            # Limit history size to prevent memory growth
            if len(self.connection_history[port]) > self.max_history_entries:
                self.connection_history[port] = self.connection_history[port][-self.max_history_entries:]