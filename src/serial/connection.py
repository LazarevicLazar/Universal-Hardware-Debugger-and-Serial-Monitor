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
    reconnect_attempt = pyqtSignal(str, int)  # port, attempt number
    
    # Constants
    MAX_BUFFER_SIZE = 1024 * 1024  # 1MB maximum buffer size
    STALLED_CONNECTION_TIMEOUT = 30  # seconds without activity to consider connection stalled
    
    def __init__(self, port, baud_rate=115200, data_bits=8, parity='N', stop_bits=1,
                 flow_control='none', auto_reconnect=True, reconnect_interval=5):
        """Initialize a serial connection"""
        super().__init__()
        
        self.port = port
        self.baud_rate = baud_rate
        self.data_bits = data_bits
        self.parity = parity
        self.stop_bits = stop_bits
        self.flow_control = flow_control
        
        # Reconnection settings
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        self.serial = None
        self.connected = False
        self.running = False
        
        # Thread synchronization
        self.stats_lock = threading.Lock()
        self.buffer_lock = threading.Lock()
        
        self.read_thread = None
        self.write_queue = queue.Queue()
        self.write_thread = None
        
        # Stalled connection detection
        self.stalled_check_timer = None
        
        self.parser = DataParser()
        
        # Connection statistics
        self.stats = {
            "bytes_received": 0,
            "bytes_sent": 0,
            "packets_received": 0,
            "packets_sent": 0,
            "errors": 0,
            "connect_time": None,
            "last_activity": None,
            "reconnect_attempts": 0,
            "stalled_detected": 0
        }
    
    def open(self):
        """Open the serial connection"""
        try:
            # Reset reconnection attempts
            self.reconnect_attempts = 0
            
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
            
            # Start stalled connection detection
            self._start_stalled_connection_detection()
            
            # Update connection status
            self.connected = True
            self.connection_status_changed.emit(self.port, True)
            
            # Update statistics with thread safety
            with self.stats_lock:
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
            
            with self.stats_lock:
                self.stats["errors"] += 1
            
            return False
        except Exception as e:
            logger.error(f"Error opening serial connection to {self.port}: {e}")
            self.error_occurred.emit(self.port, str(e))
            
            with self.stats_lock:
                self.stats["errors"] += 1
            
            return False
    
    def close(self):
        """Close the serial connection"""
        try:
            # Stop the read and write threads
            self.running = False
            
            # Stop stalled connection detection
            self._stop_stalled_connection_detection()
            
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
            
            with self.stats_lock:
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
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while self.running:
            try:
                if self.serial and self.serial.is_open:
                    # Read data from the serial port
                    data = self.serial.read(1024)
                    
                    if data:
                        # Reset error counter on successful read
                        consecutive_errors = 0
                        
                        # Update statistics with thread safety
                        with self.stats_lock:
                            self.stats["bytes_received"] += len(data)
                            self.stats["last_activity"] = datetime.now()
                        
                        # Add to buffer with thread safety and size limit
                        with self.buffer_lock:
                            # Check buffer size before adding data
                            if len(buffer) + len(data) > self.MAX_BUFFER_SIZE:
                                # Buffer would exceed max size, truncate it
                                logger.warning(f"Buffer size limit reached ({self.MAX_BUFFER_SIZE} bytes), truncating buffer")
                                buffer = buffer[-self.MAX_BUFFER_SIZE//2:]  # Keep the last half
                            
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
                            with self.stats_lock:
                                self.stats["packets_received"] += 1
                
                # Sleep to avoid high CPU usage
                time.sleep(0.01)
                
            except serial.SerialException as e:
                # Handle serial-specific errors
                logger.error(f"Serial error in read loop: {e}")
                self.error_occurred.emit(self.port, f"Serial error: {str(e)}")
                with self.stats_lock:
                    self.stats["errors"] += 1
                consecutive_errors += 1
                
                # Attempt to reconnect after serial errors
                if consecutive_errors >= max_consecutive_errors and self.auto_reconnect:
                    logger.warning(f"Too many consecutive errors, attempting to reconnect: {self.port}")
                    self._attempt_reconnect()
                    consecutive_errors = 0
                
                time.sleep(1.0)  # Sleep longer after an error
                
            except Exception as e:
                # Handle other unexpected errors
                logger.error(f"Unexpected error in read loop: {e}")
                self.error_occurred.emit(self.port, str(e))
                with self.stats_lock:
                    self.stats["errors"] += 1
                consecutive_errors += 1
                time.sleep(1.0)  # Sleep longer after an error
    
    def _write_loop(self):
        """Write data to the device in a loop"""
        consecutive_errors = 0
        max_consecutive_errors = 3
        
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
                    
                    # Reset error counter on successful write
                    consecutive_errors = 0
                    
                    # Update statistics with thread safety
                    with self.stats_lock:
                        self.stats["bytes_sent"] += len(data)
                        self.stats["packets_sent"] += 1
                        self.stats["last_activity"] = datetime.now()
                    
                    # Mark the task as done
                    self.write_queue.task_done()
                    
            except serial.SerialException as e:
                # Handle serial-specific errors
                logger.error(f"Serial error in write loop: {e}")
                self.error_occurred.emit(self.port, f"Serial write error: {str(e)}")
                with self.stats_lock:
                    self.stats["errors"] += 1
                consecutive_errors += 1
                
                # Attempt to reconnect after serial errors
                if consecutive_errors >= max_consecutive_errors and self.auto_reconnect:
                    logger.warning(f"Too many consecutive write errors, attempting to reconnect: {self.port}")
                    self._attempt_reconnect()
                    consecutive_errors = 0
                
                time.sleep(1.0)  # Sleep longer after an error
                
            except Exception as e:
                # Handle other unexpected errors
                logger.error(f"Unexpected error in write loop: {e}")
                self.error_occurred.emit(self.port, str(e))
                with self.stats_lock:
                    self.stats["errors"] += 1
                consecutive_errors += 1
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
    
    def _attempt_reconnect(self):
        """Attempt to reconnect after connection errors"""
        # Only attempt reconnection if enabled and not exceeded max attempts
        if not self.auto_reconnect or self.reconnect_attempts >= self.max_reconnect_attempts:
            if self.reconnect_attempts >= self.max_reconnect_attempts:
                logger.error(f"Maximum reconnection attempts ({self.max_reconnect_attempts}) reached for {self.port}")
            return False
        
        try:
            logger.info(f"Attempting to reconnect to {self.port} (attempt {self.reconnect_attempts + 1}/{self.max_reconnect_attempts})")
            self.reconnect_attempts += 1
            
            with self.stats_lock:
                self.stats["reconnect_attempts"] += 1
            
            # Emit reconnect attempt signal
            self.reconnect_attempt.emit(self.port, self.reconnect_attempts)
            
            # Close the current connection if it exists
            if self.serial and self.serial.is_open:
                self.serial.close()
                time.sleep(0.5)  # Short delay before reconnecting
            
            # Reopen the connection
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
            
            # Update connection status
            self.connected = True
            self.connection_status_changed.emit(self.port, True)
            
            logger.info(f"Successfully reconnected to {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reconnect to {self.port}: {e}")
            
            # Schedule another reconnection attempt after the interval
            if self.reconnect_attempts < self.max_reconnect_attempts:
                threading.Timer(self.reconnect_interval, self._attempt_reconnect).start()
            
            return False
    
    def _start_stalled_connection_detection(self):
        """Start the stalled connection detection timer"""
        self._stop_stalled_connection_detection()  # Stop any existing timer
        
        self.stalled_check_timer = threading.Timer(self.STALLED_CONNECTION_TIMEOUT / 2, self._check_stalled_connection)
        self.stalled_check_timer.daemon = True
        self.stalled_check_timer.start()
    
    def _stop_stalled_connection_detection(self):
        """Stop the stalled connection detection timer"""
        if self.stalled_check_timer:
            self.stalled_check_timer.cancel()
            self.stalled_check_timer = None
    
    def _check_stalled_connection(self):
        """Check if the connection is stalled (no activity for a long time)"""
        try:
            if not self.connected or not self.running:
                return
            
            current_time = datetime.now()
            
            with self.stats_lock:
                last_activity = self.stats["last_activity"]
            
            if last_activity:
                time_since_activity = (current_time - last_activity).total_seconds()
                
                if time_since_activity > self.STALLED_CONNECTION_TIMEOUT:
                    logger.warning(f"Stalled connection detected on {self.port}: No activity for {time_since_activity:.1f} seconds")
                    
                    with self.stats_lock:
                        self.stats["stalled_detected"] += 1
                    
                    # Attempt to reconnect if auto-reconnect is enabled
                    if self.auto_reconnect:
                        self._attempt_reconnect()
            
            # Schedule the next check
            if self.running:
                self._start_stalled_connection_detection()
                
        except Exception as e:
            logger.error(f"Error checking for stalled connection: {e}")
            # Reschedule even on error
            if self.running:
                self._start_stalled_connection_detection()


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
    
    def open_connection(self, port, baud_rate=None, data_bits=None, parity=None, stop_bits=None, flow_control=None, auto_reconnect=None, reconnect_interval=None):
        """Open a serial connection with improved error handling and reconnection"""
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
                
            if auto_reconnect is None:
                auto_reconnect = self.app.config.get("serial", "auto_reconnect", True)
                
            if reconnect_interval is None:
                reconnect_interval = self.app.config.get("serial", "reconnect_interval", 5)
            
            # Log connection attempt with detailed parameters
            logger.info(f"Attempting to open connection to {port} with settings: "
                       f"baud_rate={baud_rate}, data_bits={data_bits}, parity={parity}, "
                       f"stop_bits={stop_bits}, flow_control={flow_control}")
            
            # Check if port exists
            available_ports = [p.device for p in serial.tools.list_ports.comports()]
            if port not in available_ports:
                logger.error(f"Port {port} not found. Available ports: {available_ports}")
                return False
            
            # Create a new connection with reconnection capability
            connection = SerialConnection(
                port=port,
                baud_rate=baud_rate,
                data_bits=data_bits,
                parity=parity,
                stop_bits=stop_bits,
                flow_control=flow_control,
                auto_reconnect=auto_reconnect,
                reconnect_interval=reconnect_interval
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