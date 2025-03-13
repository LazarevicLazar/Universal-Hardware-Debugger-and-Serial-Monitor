#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Serial data parser
"""

import logging
import re
import binascii
import json
import struct

logger = logging.getLogger(__name__)

class DataParser:
    """Parses incoming data from serial connections"""
    
    # Parser modes
    MODE_TEXT = "text"
    MODE_BINARY = "binary"
    MODE_HEX = "hex"
    MODE_JSON = "json"
    MODE_CUSTOM = "custom"
    
    def __init__(self, mode=MODE_TEXT):
        """Initialize the data parser"""
        self.mode = mode
        self.buffer = bytearray()
        self.custom_pattern = None
        self.encoding = "utf-8"
    
    def set_mode(self, mode):
        """Set the parser mode"""
        if mode in [self.MODE_TEXT, self.MODE_BINARY, self.MODE_HEX, self.MODE_JSON, self.MODE_CUSTOM]:
            self.mode = mode
            logger.debug(f"Parser mode set to {mode}")
            return True
        else:
            logger.warning(f"Invalid parser mode: {mode}")
            return False
    
    def set_custom_pattern(self, pattern):
        """Set a custom regex pattern for parsing"""
        try:
            self.custom_pattern = re.compile(pattern.encode(self.encoding))
            logger.debug(f"Custom pattern set: {pattern}")
            return True
        except Exception as e:
            logger.error(f"Error setting custom pattern: {e}")
            return False
    
    def set_encoding(self, encoding):
        """Set the text encoding"""
        try:
            # Test the encoding
            "test".encode(encoding)
            
            self.encoding = encoding
            logger.debug(f"Encoding set to {encoding}")
            return True
        except Exception as e:
            logger.error(f"Invalid encoding: {e}")
            return False
    
    def process_data(self, data):
        """Process incoming data and return parsed lines/packets"""
        # Add data to the buffer
        self.buffer.extend(data)
        
        # Process based on mode
        if self.mode == self.MODE_TEXT:
            return self._process_text()
        elif self.mode == self.MODE_BINARY:
            return self._process_binary()
        elif self.mode == self.MODE_HEX:
            return self._process_hex()
        elif self.mode == self.MODE_JSON:
            return self._process_json()
        elif self.mode == self.MODE_CUSTOM:
            return self._process_custom()
        else:
            # Default to text mode
            return self._process_text()
    
    def get_remaining_buffer(self):
        """Get the remaining unprocessed data in the buffer"""
        return self.buffer
    
    def clear_buffer(self):
        """Clear the buffer"""
        self.buffer = bytearray()
    
    def _process_text(self):
        """Process text data (line-based)"""
        lines = []
        
        # Find newline characters
        while b'\n' in self.buffer or b'\r' in self.buffer:
            # Handle different line endings
            if b'\r\n' in self.buffer:
                # Windows style
                line, self.buffer = self.buffer.split(b'\r\n', 1)
                lines.append(line.decode(self.encoding, errors='replace'))
            elif b'\n' in self.buffer:
                # Unix style
                line, self.buffer = self.buffer.split(b'\n', 1)
                lines.append(line.decode(self.encoding, errors='replace'))
            elif b'\r' in self.buffer:
                # Mac style
                line, self.buffer = self.buffer.split(b'\r', 1)
                lines.append(line.decode(self.encoding, errors='replace'))
        
        return lines
    
    def _process_binary(self):
        """Process binary data (packet-based)"""
        packets = []
        
        # Look for packet start/end markers
        # This is a simple implementation that assumes packets start with 0x02 (STX) and end with 0x03 (ETX)
        while b'\x02' in self.buffer and b'\x03' in self.buffer:
            # Find the start of the packet
            start = self.buffer.find(b'\x02')
            
            # Find the end of the packet
            end = self.buffer.find(b'\x03', start)
            
            if end > start:
                # Extract the packet (excluding the markers)
                packet = self.buffer[start+1:end]
                
                # Format as hex string
                packet_hex = binascii.hexlify(packet).decode('ascii')
                packets.append(f"[BIN] {packet_hex}")
                
                # Remove the processed packet from the buffer
                self.buffer = self.buffer[end+1:]
            else:
                # Incomplete packet
                break
        
        return packets
    
    def _process_hex(self):
        """Process hex data"""
        lines = []
        
        # Process as text first
        text_lines = self._process_text()
        
        # Convert each line to a formatted hex representation
        for line in text_lines:
            try:
                # Convert to bytes
                line_bytes = line.encode(self.encoding)
                
                # Format as hex
                hex_values = ' '.join(f"{b:02X}" for b in line_bytes)
                
                lines.append(f"[HEX] {hex_values}")
            except Exception as e:
                logger.error(f"Error processing hex data: {e}")
                lines.append(f"[ERROR] {line}")
        
        return lines
    
    def _process_json(self):
        """Process JSON data"""
        lines = []
        
        # Process as text first
        text_lines = self._process_text()
        
        # Try to parse each line as JSON
        for line in text_lines:
            try:
                # Parse JSON
                json_data = json.loads(line)
                
                # Format as pretty JSON
                formatted_json = json.dumps(json_data, indent=2)
                
                lines.append(formatted_json)
            except json.JSONDecodeError:
                # Not valid JSON, pass through as-is
                lines.append(line)
            except Exception as e:
                logger.error(f"Error processing JSON data: {e}")
                lines.append(f"[ERROR] {line}")
        
        return lines
    
    def _process_custom(self):
        """Process data using a custom regex pattern"""
        if not self.custom_pattern:
            # No pattern set, process as text
            return self._process_text()
        
        matches = []
        
        # Find all matches in the buffer
        for match in self.custom_pattern.finditer(self.buffer):
            # Extract the match
            match_data = match.group(0)
            
            # Add to matches
            matches.append(match_data.decode(self.encoding, errors='replace'))
            
            # Remove from buffer up to the end of this match
            self.buffer = self.buffer[match.end():]
        
        return matches
    
    def format_data_for_display(self, data, timestamp=None):
        """Format data for display in the UI"""
        if self.mode == self.MODE_BINARY:
            # Format binary data as hex
            hex_data = ' '.join(f"{b:02X}" for b in data.encode(self.encoding, errors='replace'))
            return f"[{timestamp}] [BIN] {hex_data}" if timestamp else f"[BIN] {hex_data}"
        elif self.mode == self.MODE_HEX:
            # Format as hex
            hex_data = ' '.join(f"{b:02X}" for b in data.encode(self.encoding, errors='replace'))
            return f"[{timestamp}] [HEX] {hex_data}" if timestamp else f"[HEX] {hex_data}"
        elif self.mode == self.MODE_JSON:
            try:
                # Parse and format JSON
                json_data = json.loads(data)
                formatted_json = json.dumps(json_data, indent=2)
                return f"[{timestamp}]\n{formatted_json}" if timestamp else formatted_json
            except:
                # Not valid JSON, format as text
                return f"[{timestamp}] {data}" if timestamp else data
        else:
            # Text mode
            return f"[{timestamp}] {data}" if timestamp else data
    
    def parse_command(self, command):
        """Parse a command for sending"""
        if command.startswith("\\x"):
            # Hex command
            try:
                # Convert hex string to bytes
                hex_cmd = command.replace("\\x", "")
                hex_bytes = bytes.fromhex(hex_cmd)
                return hex_bytes
            except Exception as e:
                logger.error(f"Error parsing hex command: {e}")
                return command.encode(self.encoding)
        elif command.startswith("\\b"):
            # Binary command
            try:
                # Convert binary string to bytes
                bin_cmd = command.replace("\\b", "")
                bin_bytes = int(bin_cmd, 2).to_bytes((len(bin_cmd) + 7) // 8, byteorder='big')
                return bin_bytes
            except Exception as e:
                logger.error(f"Error parsing binary command: {e}")
                return command.encode(self.encoding)
        else:
            # Text command
            return command.encode(self.encoding)