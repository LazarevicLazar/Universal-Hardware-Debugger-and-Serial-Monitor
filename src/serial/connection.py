#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Serial connection management
"""

import logging
import threading
import time
import queue
from datetime import datetime

import serial
from PyQt6.QtCore import QObject, pyqtSignal

from src.serial.parser import DataParser

logger = logging.getLogger(__name__)

class SerialConnection(QObject):
    """Manages a single serial connection to a device"""
    
    # Signals
    data_received = pyqtSignal(str, str, str)  # port, data, timestamp
    connection_status_changed = pyqtSignal(str, bool)  # port, connected
    error_occurred = pyqtSignal(str, str)  # port, error message
    
    def __init__(self, port, baud_rate=115200, data_bits=8, parity='N', stop_bits=1, flow_control='none'):
        """Initialize a serial connection"""
        super().__init__()
        
        self.port = port
        self.baud_rate = baud_rate
        self.data_bits = data_bits
        self.parity = parity
        self.stop_bits = stop_bits
        self.flow_control = flow_control
        
        self.serial = None
        self.connected = False
        self.running = False
        
        self.read_thread = None
        self.write_queue = queue.Queue()
        self.write_thread = None
        
        self.parser = DataParser()
        
        # Connection statistics
        self.stats = {
            "bytes_received": 0,
            "bytes_sent": 0,
            "packets_received": 0,
            "packets_sent": 0,
            "errors": 0,
            "connect_time": None,
            "last_activity": None
        }
    
    def open(self):
        """Open the serial connection"""
        try:
            # Log detailed connection attempt
            logger.info(f"Opening serial connection to {self.port} with settings: "
                       f"baud_rate={self.baud_rate}, data_bits={self.data_bits}, "
                       f"parity={self.parity}, stop_bits={self.stop_bits}, "
                       f"flow_control={self.flow_control}")
            
            # Configure the serial port
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                bytesize=self.data_bits,
                parity=self.parity,
                stopbits=self.stop_bits,
                xonxoff=(self.flow_control == 'xonxoff'),
                rtscts=(self.flow_control == 'rtscts'),
                dsrdtr=(self.flow_control == 'dsrdtr'),
                timeout=0.1
            )
            
            # Start the read and write threads
            self.running = True
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            
            self.write_thread = threading.Thread(target=self._write_loop, daemon=True)
            self.write_thread.start()
            
            # Update connection status
            self.connected = True
            self.connection_status_changed.emit(self.port, True)
            
            # Update statistics
            self.stats["connect_time"] = datetime.now()
            self.stats["last_activity"] = datetime.now()
            
            logger.info(f"Serial connection opened successfully: {self.port} at {self.baud_rate} baud")
            return True
        except serial.SerialException as e:
            error_msg = str(e)
            if "Access is denied" in error_msg:
                logger.error(f"Access denied to {self.port}. The port may be in use by another application.")
                self.error_occurred.emit(self.port, f"Access denied to {self.port}. The port may be in use by another application.")
            elif "Port not found" in error_msg or "No such file or directory" in error_msg:
                logger.error(f"Port {self.port} not found. Please check the port name.")
                self.error_occurred.emit(self.port, f"Port {self.port} not found. Please check the port name.")
            elif "Permission denied" in error_msg:
                logger.error(f"Permission denied for {self.port}. You may need elevated privileges.")
                self.error_occurred.emit(self.port, f"Permission denied for {self.port}. You may need elevated privileges.")
            else:
                logger.error(f"Serial error opening connection to {self.port}: {e}")
                self.error_occurred.emit(self.port, f"Serial error: {error_msg}")
            self.stats["errors"] += 1
            return False
        except Exception as e:
            logger.error(f"Error opening serial connection to {self.port}: {e}")
            self.error_occurred.emit(self.port, str(e))
            self.stats["errors"] += 1
            return False
    
    def close(self):
        """Close the serial connection"""
        try:
            # Stop the read and write threads
            self.running = False
            
            if self.read_thread and self.read_thread.is_alive():
                self.read_thread.join(timeout=1.0)
            
            if self.write_thread and self.write_thread.is_alive():
                self.write_thread.join(timeout=1.0)
            
            # Close the serial port
            if self.serial and self.serial.is_open:
                self.serial.close()
            
            # Update connection status
            self.connected = False
            self.connection_status_changed.emit(self.port, False)
            
            logger.info(f"Serial connection closed: {self.port}")
            return True
        except Exception as e:
            logger.error(f"Error closing serial connection: {e}")
            self.error_occurred.emit(self.port, str(e))
            self.stats["errors"] += 1
            return False
    
    def send(self, data, add_newline=True):
        """Send data to the device"""
        try:
            if not self.connected:
                logger.warning(f"Cannot send data: connection is closed ({self.port})")
                return False
            
            # Add newline if requested
            if add_newline and not data.endswith('\n'):
                data += '\n'
            
            # Add to the write queue
            self.write_queue.put(data)
            
            return True
        except Exception as e:
            logger.error(f"Error sending data: {e}")
            self.error_occurred.emit(self.port, str(e))
            self.stats["errors"] += 1
            return False
    
    def _read_loop(self):
        """Read data from the device in a loop"""
        buffer = bytearray()
        
        while self.running:
            try:
                if self.serial and self.serial.is_open:
                    # Read data from the serial port
                    data = self.serial.read(1024)
                    
                    if data:
                        # Update statistics
                        self.stats["bytes_received"] += len(data)
                        self.stats["last_activity"] = datetime.now()
                        
                        # Add to buffer
                        buffer.extend(data)
                        
                        # Process the buffer
                        lines = self.parser.process_data(buffer)
                        
                        # Clear the processed data from the buffer
                        buffer = bytearray(self.parser.get_remaining_buffer())
                        
                        # Emit signals for each line
                        for line in lines:
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                            self.data_received.emit(self.port, line, timestamp)
                            self.stats["packets_received"] += 1
                
                # Sleep to avoid high CPU usage
                time.sleep(0.01)
            except Exception as e:
                logger.error(f"Error in read loop: {e}")
                self.error_occurred.emit(self.port, str(e))
                self.stats["errors"] += 1
                time.sleep(1.0)  # Sleep longer after an error
    
    def _write_loop(self):
        """Write data to the device in a loop"""
        while self.running:
            try:
                # Get data from the write queue
                try:
                    data = self.write_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                if self.serial and self.serial.is_open:
                    # Convert to bytes if necessary
                    if isinstance(data, str):
                        data = data.encode('utf-8')
                    
                    # Write to the serial port
                    self.serial.write(data)
                    self.serial.flush()
                    
                    # Update statistics
                    self.stats["bytes_sent"] += len(data)
                    self.stats["packets_sent"] += 1
                    self.stats["last_activity"] = datetime.now()
                    
                    # Mark the task as done
                    self.write_queue.task_done()
            except Exception as e:
                logger.error(f"Error in write loop: {e}")
                self.error_occurred.emit(self.port, str(e))
                self.stats["errors"] += 1
                time.sleep(1.0)  # Sleep longer after an error
    
    def get_statistics(self):
        """Get connection statistics"""
        return self.stats
    
    def get_connection_info(self):
        """Get connection information"""
        return {
            "port": self.port,
            "baud_rate": self.baud_rate,
            "data_bits": self.data_bits,
            "parity": self.parity,
            "stop_bits": self.stop_bits,
            "flow_control": self.flow_control,
            "connected": self.connected,
            "statistics": self.get_statistics()
        }
    
    def set_parser_mode(self, mode):
        """Set the parser mode"""
        self.parser.set_mode(mode)


class SerialConnectionManager(QObject):
    """Manages multiple serial connections"""
    
    # Signals
    connection_added = pyqtSignal(str)  # port
    connection_removed = pyqtSignal(str)  # port
    
    def __init__(self, app):
        """Initialize the serial connection manager"""
        super().__init__()
        
        self.app = app
        self.connections = {}
    
    def open_connection(self, port, baud_rate=None, data_bits=None, parity=None, stop_bits=None, flow_control=None):
        """Open a serial connection"""
        try:
            # Check if already connected
            if port in self.connections and self.connections[port].connected:
                logger.warning(f"Connection already open: {port}")
                return True
            
            # Use default settings if not specified
            if baud_rate is None:
                baud_rate = self.app.config.get("serial", "default_baud_rate", 115200)
            
            if data_bits is None:
                data_bits = self.app.config.get("serial", "default_data_bits", 8)
            
            if parity is None:
                parity = self.app.config.get("serial", "default_parity", "N")
            
            if stop_bits is None:
                stop_bits = self.app.config.get("serial", "default_stop_bits", 1)
            
            if flow_control is None:
                flow_control = self.app.config.get("serial", "default_flow_control", "none")
            
            # Log connection attempt with detailed parameters
            logger.info(f"Attempting to open connection to {port} with settings: "
                       f"baud_rate={baud_rate}, data_bits={data_bits}, parity={parity}, "
                       f"stop_bits={stop_bits}, flow_control={flow_control}")
            
            # Check if port exists
            available_ports = [p.device for p in serial.tools.list_ports.comports()]
            if port not in available_ports:
                logger.error(f"Port {port} not found. Available ports: {available_ports}")
                return False
            
            # Create a new connection
            connection = SerialConnection(
                port=port,
                baud_rate=baud_rate,
                data_bits=data_bits,
                parity=parity,
                stop_bits=stop_bits,
                flow_control=flow_control
            )
            
            # Connect signals
            connection.data_received.connect(self._on_data_received)
            connection.connection_status_changed.connect(self._on_connection_status_changed)
            connection.error_occurred.connect(self._on_error_occurred)
            
            # Open the connection
            if connection.open():
                # Add to the connections dictionary
                self.connections[port] = connection
                
                # Emit signal
                self.connection_added.emit(port)
                
                logger.info(f"Successfully opened connection to {port}")
                return True
            else:
                logger.error(f"Failed to open connection to {port}")
                return False
        except serial.SerialException as e:
            error_msg = str(e)
            if "Access is denied" in error_msg:
                logger.error(f"Access denied to {port}. The port may be in use by another application.")
            elif "Port not found" in error_msg:
                logger.error(f"Port {port} not found. Please check the port name.")
            elif "Permission denied" in error_msg:
                logger.error(f"Permission denied for {port}. You may need elevated privileges.")
            else:
                logger.error(f"Serial error opening connection to {port}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error opening connection to {port}: {e}")
            return False
    
    def close_connection(self, port):
        """Close a serial connection"""
        try:
            # Check if connected
            if port not in self.connections:
                logger.warning(f"Connection not found: {port}")
                return True
            
            # Close the connection
            if self.connections[port].close():
                # Remove from the connections dictionary
                connection = self.connections.pop(port)
                
                # Disconnect signals
                connection.data_received.disconnect(self._on_data_received)
                connection.connection_status_changed.disconnect(self._on_connection_status_changed)
                connection.error_occurred.disconnect(self._on_error_occurred)
                
                # Emit signal
                self.connection_removed.emit(port)
                
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
            return False
    
    def close_all_connections(self):
        """Close all serial connections"""
        ports = list(self.connections.keys())
        
        for port in ports:
            self.close_connection(port)
    
    def send_data(self, port, data, add_newline=True):
        """Send data to a device"""
        try:
            # Check if connected
            if port not in self.connections:
                logger.warning(f"Connection not found: {port}")
                return False
            
            # Send the data
            return self.connections[port].send(data, add_newline)
        except Exception as e:
            logger.error(f"Error sending data: {e}")
            return False
    
    def broadcast_data(self, data, add_newline=True):
        """Send data to all connected devices"""
        success = True
        
        for port, connection in self.connections.items():
            if connection.connected:
                if not connection.send(data, add_newline):
                    success = False
        
        return success
    
    def get_connection(self, port):
        """Get a connection by port"""
        return self.connections.get(port, None)
    
    def get_connections(self):
        """Get all connections"""
        return self.connections
    
    def get_connection_list(self):
        """Get a list of connection information"""
        return [connection.get_connection_info() for connection in self.connections.values()]
    
    def restore_connections(self, connections):
        """Restore connections from a saved session"""
        for conn_info in connections:
            # Open the connection with the saved settings
            self.open_connection(
                port=conn_info["port"],
                baud_rate=conn_info["baud_rate"],
                data_bits=conn_info["data_bits"],
                parity=conn_info["parity"],
                stop_bits=conn_info["stop_bits"],
                flow_control=conn_info["flow_control"]
            )
    
    def _on_data_received(self, port, data, timestamp):
        """Handle data received from a device"""
        # Forward to the serial monitor panel
        if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'serial_monitor'):
            self.app.main_window.serial_monitor.add_data(port, data, timestamp)
    
    def _on_connection_status_changed(self, port, connected):
        """Handle connection status changes"""
        # Update the device panel
        if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'device_panel'):
            self.app.main_window.device_panel.update_device_list()
    
    def _on_error_occurred(self, port, error):
        """Handle connection errors"""
        # Show error in the status bar
        if hasattr(self.app, 'main_window'):
            self.app.main_window.statusBar().showMessage(f"Error on {port}: {error}", 5000)