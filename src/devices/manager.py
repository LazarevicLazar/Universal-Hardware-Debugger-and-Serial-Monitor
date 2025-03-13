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
    
    def __init__(self, app):
        """Initialize the device manager"""
        self.app = app
        
        # List of detected devices
        self.devices = []
        
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
        """Scan for connected devices"""
        try:
            # Get list of serial ports
            ports = list(serial.tools.list_ports.comports())
            logger.info(f"Found {len(ports)} serial ports")
            
            # Create a list of new devices
            new_devices = []
            
            for port in ports:
                # Create a device ID from VID:PID
                vid_pid = f"{port.vid:04X}:{port.pid:04X}" if port.vid and port.pid else None
                
                # Log port details for debugging
                logger.info(f"Port: {port.device}, Description: {port.description}, VID:PID: {vid_pid}, HWID: {port.hwid}")
                
                # Check if this is a known device
                device_info = self.KNOWN_DEVICES.get(vid_pid, None) if vid_pid else None
                
                if device_info:
                    logger.info(f"Recognized as: {device_info['name']} ({device_info['type']})")
                else:
                    logger.info(f"Unrecognized device")
                
                # Create device entry
                device = {
                    "port": port.device,
                    "description": port.description,
                    "hardware_id": port.hwid,
                    "vid_pid": vid_pid,
                    "name": device_info["name"] if device_info else port.description,
                    "type": device_info["type"] if device_info else "unknown",
                    "connected": False,
                    "last_seen": time.time()
                }
                
                # Add to new devices list
                new_devices.append(device)
            
            # Update the devices list
            self._update_device_list(new_devices)
            
            return self.devices
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
        
        # Add or update devices
        for port, device in new_devices_dict.items():
            if port in current_devices:
                # Update existing device
                current_devices[port]["last_seen"] = time.time()
                updated_devices.append(current_devices[port])
            else:
                # New device
                logger.info(f"New device detected: {device['name']} on {port}")
                
                # Auto-connect if enabled
                if self.app.config.get("devices", "auto_connect", True):
                    self.connect_device(device)
                
                updated_devices.append(device)
        
        # Check for disconnected devices
        current_time = time.time()
        timeout = 5  # seconds
        
        for port, device in current_devices.items():
            if port not in new_devices_dict:
                # Device not seen in this scan
                if current_time - device["last_seen"] > timeout:
                    # Device has been gone for too long, consider it disconnected
                    logger.info(f"Device disconnected: {device['name']} on {port}")
                    
                    # Disconnect if connected
                    if device["connected"]:
                        self.disconnect_device(device)
                else:
                    # Device might be temporarily unavailable, keep it in the list
                    updated_devices.append(device)
        
        # Update the devices list
        self.devices = updated_devices
        
        # Notify the UI of changes
        if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'device_panel'):
            self.app.main_window.device_panel.update_device_list()
    
    def connect_device(self, device):
        """Connect to a device"""
        try:
            # Check if already connected
            if device["connected"]:
                logger.warning(f"Device already connected: {device['name']} on {device['port']}")
                return True
            
            # Connect to the device using the serial manager
            if self.app.serial_manager.open_connection(device["port"]):
                # Update device status
                device["connected"] = True
                logger.info(f"Connected to device: {device['name']} on {device['port']}")
                
                # Notify the UI of changes
                if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'device_panel'):
                    self.app.main_window.device_panel.update_device_list()
                
                return True
            else:
                logger.error(f"Failed to connect to device: {device['name']} on {device['port']}")
                return False
        except Exception as e:
            logger.error(f"Error connecting to device: {e}")
            return False
    
    def disconnect_device(self, device):
        """Disconnect from a device"""
        try:
            # Check if connected
            if not device["connected"]:
                logger.warning(f"Device not connected: {device['name']} on {device['port']}")
                return True
            
            # Disconnect from the device using the serial manager
            if self.app.serial_manager.close_connection(device["port"]):
                # Update device status
                device["connected"] = False
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
        for device in self.devices:
            if device["port"] == port:
                return device
        return None
    
    def get_device_list(self):
        """Get the list of detected devices"""
        return self.devices
    
    def get_connected_devices(self):
        """Get the list of connected devices"""
        return [d for d in self.devices if d["connected"]]
    
    def restore_devices(self, devices):
        """Restore device connections from a saved session"""
        for saved_device in devices:
            # Find the device in the current list
            device = self.get_device_by_port(saved_device["port"])
            
            if device and saved_device["connected"]:
                # Connect to the device
                self.connect_device(device)
    
    def add_custom_device(self, vid_pid, name, device_type):
        """Add a custom device to the database"""
        try:
            # Add to the known devices dictionary
            self.KNOWN_DEVICES[vid_pid] = {"name": name, "type": device_type}
            
            # Save the updated database
            with open(self.device_db_path, 'w') as f:
                json.dump(self.KNOWN_DEVICES, f, indent=4)
            
            logger.info(f"Added custom device: {name} ({vid_pid})")
            return True
        except Exception as e:
            logger.error(f"Error adding custom device: {e}")
            return False
            
    def add_manual_port(self, port, device_type="unknown", name=None):
        """Add a manual port that isn't automatically detected"""
        try:
            # Check if the port already exists
            existing_device = self.get_device_by_port(port)
            if existing_device:
                logger.info(f"Port {port} already exists as {existing_device['name']}")
                return existing_device
            
            # Create a device entry
            device = {
                "port": port,
                "description": name or f"Manual {device_type.capitalize()} Device",
                "hardware_id": "MANUAL",
                "vid_pid": None,
                "name": name or f"Manual {device_type.capitalize()} Device on {port}",
                "type": device_type,
                "connected": False,
                "last_seen": time.time(),
                "manual": True  # Flag to indicate this is a manually added device
            }
            
            # Add to devices list
            self.devices.append(device)
            logger.info(f"Manually added device: {device['name']} on {port}")
            
            # Notify the UI of changes
            if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'device_panel'):
                self.app.main_window.device_panel.update_device_list()
            
            return device
        except Exception as e:
            logger.error(f"Error adding manual port: {e}")
            return None