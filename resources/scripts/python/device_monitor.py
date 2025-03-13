#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Device Monitor Script
This script demonstrates the Python scripting capabilities
"""

import time
import re
import json

def main():
    """Main entry point for the script"""
    print("Device Monitor Script Started")
    
    # Get connected devices
    devices = device_manager.get_connected_devices()
    print(f"Connected devices: {len(devices)}")
    
    if not devices:
        print("No devices connected. Please connect a device and try again.")
        return
    
    # Monitor each device
    for device in devices:
        print(f"\nMonitoring device: {device['name']} on {device['port']}")
        
        # Send version query
        print("Sending version query...")
        command_interface.send_command(device['port'], "AT+GMR")
        time.sleep(1)
        
        # Send system info query
        print("Sending system info query...")
        command_interface.send_command(device['port'], "AT+SYSINFO")
        time.sleep(1)
        
        # Set up a pattern to monitor temperature data
        print("Setting up temperature monitoring...")
        print("(This would normally extract temperature data from device output)")
        
        # Simulate monitoring for a few seconds
        for i in range(5):
            print(f"Monitoring cycle {i+1}...")
            
            # In a real script, we would extract data from the serial output
            # For demonstration, we'll simulate some data
            temp = 25.0 + (i * 0.5)
            humidity = 50.0 + (i * 1.0)
            
            print(f"Temperature: {temp}°C, Humidity: {humidity}%")
            time.sleep(1)
    
    print("\nDevice monitoring completed")

if __name__ == "__main__":
    main()