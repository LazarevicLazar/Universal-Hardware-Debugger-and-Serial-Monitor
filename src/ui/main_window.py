#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Main application window
"""

import logging
import platform
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QMenu, QToolBar,
    QStatusBar, QFileDialog, QMessageBox, QTabWidget,
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QInputDialog
)
from PyQt6.QtCore import Qt, QSize, QSettings, QTimer
from PyQt6.QtGui import QIcon, QKeySequence, QAction

from src.ui.device_panel import DevicePanel
from src.ui.serial_monitor import SerialMonitor
from src.ui.visualization import VisualizationPanel
from src.ui.command_center import CommandCenter
from src.ui.script_editor import ScriptEditor

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Main application window for the Universal Hardware Debugger and Serial Monitor"""
    
    def __init__(self, app):
        """Initialize the main window"""
        super().__init__()
        
        self.app = app
        
        # Set window properties
        self.setWindowTitle("Universal Hardware Debugger and Serial Monitor")
        self.setMinimumSize(1024, 768)
        
        # Initialize UI components
        self._init_ui()
        
        # Restore window state
        self._restore_window_state()
        
        # Status update timer
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)  # Update every second
        
        logger.info("Main window initialized")
    
    def _init_ui(self):
        """Initialize the UI components"""
        # Create the central widget
        self.central_widget = QTabWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create the panels
        self._create_panels()
        
        # Create the menu bar
        self._create_menu_bar()
        
        # Create the toolbar
        self._create_toolbar()
        
        # Create the status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Add device count label to status bar
        self.device_count_label = QLabel("Devices: 0")
        self.status_bar.addPermanentWidget(self.device_count_label)
        
        # Add connection count label to status bar
        self.connection_count_label = QLabel("Connections: 0")
        self.status_bar.addPermanentWidget(self.connection_count_label)
    
    def _create_panels(self):
        """Create the application panels"""
        # Device Panel
        self.device_panel = DevicePanel(self.app)
        self.device_dock = QDockWidget("Devices", self)
        self.device_dock.setWidget(self.device_panel)
        self.device_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.device_dock)
        
        # Serial Monitor
        self.serial_monitor = SerialMonitor(self.app)
        self.central_widget.addTab(self.serial_monitor, "Serial Monitor")
        
        # Visualization Panel
        self.visualization_panel = VisualizationPanel(self.app)
        self.central_widget.addTab(self.visualization_panel, "Visualization")
        
        # Command Center
        self.command_center = CommandCenter(self.app)
        self.command_dock = QDockWidget("Command Center", self)
        self.command_dock.setWidget(self.command_center)
        self.command_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.command_dock)
        
        # Script Editor
        self.script_editor = ScriptEditor(self.app)
        self.central_widget.addTab(self.script_editor, "Script Editor")
    
    def _create_menu_bar(self):
        """Create the menu bar"""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        # New Session
        new_session_action = QAction("&New Session", self)
        new_session_action.setShortcut(QKeySequence.StandardKey.New)
        new_session_action.triggered.connect(self._new_session)
        file_menu.addAction(new_session_action)
        
        # Open Session
        open_session_action = QAction("&Open Session", self)
        open_session_action.setShortcut(QKeySequence.StandardKey.Open)
        open_session_action.triggered.connect(self._open_session)
        file_menu.addAction(open_session_action)
        
        # Save Session
        save_session_action = QAction("&Save Session", self)
        save_session_action.setShortcut(QKeySequence.StandardKey.Save)
        save_session_action.triggered.connect(self._save_session)
        file_menu.addAction(save_session_action)
        
        # Save Session As
        save_session_as_action = QAction("Save Session &As...", self)
        save_session_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_session_as_action.triggered.connect(self._save_session_as)
        file_menu.addAction(save_session_as_action)
        
        file_menu.addSeparator()
        
        # Export Logs
        export_logs_action = QAction("&Export Logs...", self)
        export_logs_action.triggered.connect(self._export_logs)
        file_menu.addAction(export_logs_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Device menu
        device_menu = self.menuBar().addMenu("&Device")
        
        # Scan Devices
        scan_devices_action = QAction("&Scan for Devices", self)
        scan_devices_action.setShortcut("F5")
        scan_devices_action.triggered.connect(self._scan_devices)
        device_menu.addAction(scan_devices_action)
        
        # Connect All
        connect_all_action = QAction("Connect &All Devices", self)
        connect_all_action.triggered.connect(self._connect_all_devices)
        device_menu.addAction(connect_all_action)
        
        # Disconnect All
        disconnect_all_action = QAction("&Disconnect All Devices", self)
        disconnect_all_action.triggered.connect(self._disconnect_all_devices)
        device_menu.addAction(disconnect_all_action)
        
        device_menu.addSeparator()
        
        # Device Settings
        device_settings_action = QAction("Device &Settings...", self)
        device_settings_action.triggered.connect(self._device_settings)
        device_menu.addAction(device_settings_action)
        
        device_menu.addSeparator()
        
        # Add Manual Port
        add_manual_port_action = QAction("Add &Manual Port...", self)
        add_manual_port_action.triggered.connect(self._add_manual_port)
        device_menu.addAction(add_manual_port_action)
        
        # Direct Connect
        direct_connect_action = QAction("&Direct Connect to COM Port...", self)
        direct_connect_action.triggered.connect(lambda: self._direct_connect_dialog())
        device_menu.addAction(direct_connect_action)
        
        # View menu
        view_menu = self.menuBar().addMenu("&View")
        
        # Device Panel
        device_panel_action = QAction("&Device Panel", self)
        device_panel_action.setCheckable(True)
        device_panel_action.setChecked(True)
        device_panel_action.triggered.connect(lambda checked: self.device_dock.setVisible(checked))
        view_menu.addAction(device_panel_action)
        
        # Command Center
        command_center_action = QAction("&Command Center", self)
        command_center_action.setCheckable(True)
        command_center_action.setChecked(True)
        command_center_action.triggered.connect(lambda checked: self.command_dock.setVisible(checked))
        view_menu.addAction(command_center_action)
        
        view_menu.addSeparator()
        
        # Reset Layout
        reset_layout_action = QAction("&Reset Layout", self)
        reset_layout_action.triggered.connect(self._reset_layout)
        view_menu.addAction(reset_layout_action)
        
        # Tools menu
        tools_menu = self.menuBar().addMenu("&Tools")
        
        # Serial Terminal
        serial_terminal_action = QAction("Serial &Terminal", self)
        serial_terminal_action.triggered.connect(lambda: self.central_widget.setCurrentWidget(self.serial_monitor))
        tools_menu.addAction(serial_terminal_action)
        
        # Visualization
        visualization_action = QAction("&Visualization", self)
        visualization_action.triggered.connect(lambda: self.central_widget.setCurrentWidget(self.visualization_panel))
        tools_menu.addAction(visualization_action)
        
        # Script Editor
        script_editor_action = QAction("&Script Editor", self)
        script_editor_action.triggered.connect(lambda: self.central_widget.setCurrentWidget(self.script_editor))
        tools_menu.addAction(script_editor_action)
        
        tools_menu.addSeparator()
        
        # Options
        options_action = QAction("&Options...", self)
        options_action.triggered.connect(self._show_options)
        tools_menu.addAction(options_action)
        
        tools_menu.addSeparator()
        
        # Check Available Ports
        check_ports_action = QAction("&Check Available Ports", self)
        check_ports_action.triggered.connect(self._check_available_ports)
        tools_menu.addAction(check_ports_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        # About
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        # Documentation
        docs_action = QAction("&Documentation", self)
        docs_action.triggered.connect(self._show_documentation)
        help_menu.addAction(docs_action)
    
    def _create_toolbar(self):
        """Create the toolbar"""
        # Main toolbar
        self.toolbar = QToolBar("Main Toolbar", self)
        self.toolbar.setMovable(True)
        self.addToolBar(self.toolbar)
        
        # Scan Devices
        scan_action = QAction("Scan Devices", self)
        scan_action.triggered.connect(self._scan_devices)
        self.toolbar.addAction(scan_action)
        
        # Connect All
        connect_all_action = QAction("Connect All", self)
        connect_all_action.triggered.connect(self._connect_all_devices)
        self.toolbar.addAction(connect_all_action)
        
        # Disconnect All
        disconnect_all_action = QAction("Disconnect All", self)
        disconnect_all_action.triggered.connect(self._disconnect_all_devices)
        self.toolbar.addAction(disconnect_all_action)
        
        self.toolbar.addSeparator()
        
        # Clear Terminal
        clear_terminal_action = QAction("Clear Terminal", self)
        clear_terminal_action.triggered.connect(self._clear_terminal)
        self.toolbar.addAction(clear_terminal_action)
        
        # Export Logs
        export_logs_action = QAction("Export Logs", self)
        export_logs_action.triggered.connect(self._export_logs)
        self.toolbar.addAction(export_logs_action)
        
        self.toolbar.addSeparator()
        
        # Add Manual Port
        add_manual_port_action = QAction("Add Manual Port", self)
        add_manual_port_action.triggered.connect(self._add_manual_port)
        self.toolbar.addAction(add_manual_port_action)
        
        # Direct Connect
        direct_connect_action = QAction("Direct Connect", self)
        direct_connect_action.triggered.connect(lambda: self._direct_connect_dialog())
        self.toolbar.addAction(direct_connect_action)
    
    def _restore_window_state(self):
        """Restore the window state from settings"""
        try:
            # Get window settings
            window_size = self.app.config.get("ui", "window_size", [1024, 768])
            window_position = self.app.config.get("ui", "window_position", [100, 100])
            window_maximized = self.app.config.get("ui", "window_maximized", False)
            
            # Apply settings
            self.resize(window_size[0], window_size[1])
            self.move(window_position[0], window_position[1])
            
            if window_maximized:
                self.showMaximized()
        except Exception as e:
            logger.error(f"Error restoring window state: {e}")
    
    def _save_window_state(self):
        """Save the window state to settings"""
        try:
            # Save window settings
            if not self.isMaximized():
                self.app.config.set("ui", "window_size", [self.width(), self.height()])
                self.app.config.set("ui", "window_position", [self.x(), self.y()])
            
            self.app.config.set("ui", "window_maximized", self.isMaximized())
        except Exception as e:
            logger.error(f"Error saving window state: {e}")
    
    def _update_status(self):
        """Update the status bar with current information"""
        try:
            # Update device count
            device_count = len(self.app.device_manager.get_device_list())
            connected_count = len(self.app.device_manager.get_connected_devices())
            self.device_count_label.setText(f"Devices: {connected_count}/{device_count}")
            
            # Update connection count
            connection_count = len(self.app.serial_manager.get_connections())
            self.connection_count_label.setText(f"Connections: {connection_count}")
        except Exception as e:
            logger.error(f"Error updating status: {e}")
    
    def _new_session(self):
        """Create a new session"""
        try:
            # Confirm with the user
            reply = QMessageBox.question(
                self, "New Session",
                "Create a new session? This will save the current session first.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Create a new session
                self.app.session_manager.create_new_session()
                
                # Disconnect all devices
                self._disconnect_all_devices()
                
                # Clear the terminal
                self._clear_terminal()
                
                # Update the UI
                self.status_bar.showMessage("New session created", 3000)
        except Exception as e:
            logger.error(f"Error creating new session: {e}")
            QMessageBox.critical(self, "Error", f"Error creating new session: {e}")
    
    def _open_session(self):
        """Open a saved session"""
        try:
            # Get the list of saved sessions
            sessions = self.app.session_manager.list_sessions()
            
            if not sessions:
                QMessageBox.information(self, "Open Session", "No saved sessions found.")
                return
            
            # TODO: Show a session selection dialog
            # For now, just load the most recent session
            self.app.session_manager.load_last_session()
            
            # Update the UI
            self.status_bar.showMessage("Session loaded", 3000)
        except Exception as e:
            logger.error(f"Error opening session: {e}")
            QMessageBox.critical(self, "Error", f"Error opening session: {e}")
    
    def _save_session(self):
        """Save the current session"""
        try:
            # Save the session
            if self.app.session_manager.save_current_session():
                self.status_bar.showMessage("Session saved", 3000)
            else:
                QMessageBox.warning(self, "Save Session", "Error saving session.")
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            QMessageBox.critical(self, "Error", f"Error saving session: {e}")
    
    def _save_session_as(self):
        """Save the current session with a new name"""
        try:
            # TODO: Show a dialog to enter a new session name
            # For now, just save with the current name
            self._save_session()
        except Exception as e:
            logger.error(f"Error saving session as: {e}")
            QMessageBox.critical(self, "Error", f"Error saving session: {e}")
    
    def _export_logs(self):
        """Export logs to a file"""
        try:
            # Show a file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Logs", "", "CSV Files (*.csv);;JSON Files (*.json);;Text Files (*.txt)"
            )
            
            if not file_path:
                return
            
            # Determine the export format based on the file extension
            if file_path.endswith(".csv"):
                format = "csv"
            elif file_path.endswith(".json"):
                format = "json"
            else:
                format = "txt"
            
            # Export the logs
            if self.serial_monitor.export_logs(file_path, format):
                self.status_bar.showMessage(f"Logs exported to {file_path}", 3000)
            else:
                QMessageBox.warning(self, "Export Logs", "Error exporting logs.")
        except Exception as e:
            logger.error(f"Error exporting logs: {e}")
            QMessageBox.critical(self, "Error", f"Error exporting logs: {e}")
    
    def _scan_devices(self):
        """Scan for connected devices"""
        try:
            # Scan for devices
            devices = self.app.device_manager.scan_devices()
            
            # Update the status bar
            self.status_bar.showMessage(f"Found {len(devices)} devices", 3000)
        except Exception as e:
            logger.error(f"Error scanning for devices: {e}")
            QMessageBox.critical(self, "Error", f"Error scanning for devices: {e}")
    
    def _connect_all_devices(self):
        """Connect to all detected devices"""
        try:
            # Get the list of devices
            devices = self.app.device_manager.get_device_list()
            
            if not devices:
                QMessageBox.information(self, "Connect All", "No devices detected.")
                return
            
            # Connect to each device
            connected = 0
            for device in devices:
                if not device["connected"]:
                    if self.app.device_manager.connect_device(device):
                        connected += 1
            
            # Update the status bar
            self.status_bar.showMessage(f"Connected to {connected} devices", 3000)
        except Exception as e:
            logger.error(f"Error connecting to devices: {e}")
            QMessageBox.critical(self, "Error", f"Error connecting to devices: {e}")
    
    def _disconnect_all_devices(self):
        """Disconnect from all connected devices"""
        try:
            # Get the list of connected devices
            devices = self.app.device_manager.get_connected_devices()
            
            if not devices:
                QMessageBox.information(self, "Disconnect All", "No devices connected.")
                return
            
            # Disconnect from each device
            disconnected = 0
            for device in devices:
                if self.app.device_manager.disconnect_device(device):
                    disconnected += 1
            
            # Update the status bar
            self.status_bar.showMessage(f"Disconnected from {disconnected} devices", 3000)
        except Exception as e:
            logger.error(f"Error disconnecting from devices: {e}")
            QMessageBox.critical(self, "Error", f"Error disconnecting from devices: {e}")
    
    def _device_settings(self):
        """Show the device settings dialog"""
        try:
            # TODO: Implement device settings dialog
            QMessageBox.information(self, "Device Settings", "Device settings dialog not implemented yet.")
        except Exception as e:
            logger.error(f"Error showing device settings: {e}")
            QMessageBox.critical(self, "Error", f"Error showing device settings: {e}")
            
    def _add_manual_port(self):
        """Add a manual serial port"""
        try:
            # Show a dialog to enter port details
            port, ok = QInputDialog.getText(self, "Add Manual Port", "Enter port name (e.g., COM3):")
            if ok and port:
                # Add the port
                device = self.app.device_manager.add_manual_port(port, "esp32", f"ESP32 on {port}")
                if device:
                    # Connect to the device
                    success = self.app.device_manager.connect_device(device)
                    if success:
                        self.status_bar.showMessage(f"Added and connected to {device['name']}", 3000)
                    else:
                        # Try direct connection if device manager connection fails
                        self._direct_connect_port(port)
                else:
                    QMessageBox.warning(self, "Add Manual Port", f"Failed to add port {port}")
        except Exception as e:
            logger.error(f"Error adding manual port: {e}")
            QMessageBox.critical(self, "Error", f"Error adding manual port: {e}")
            
    def _direct_connect_dialog(self):
        """Show dialog to directly connect to a COM port"""
        try:
            # Get list of available ports
            import serial.tools.list_ports
            available_ports = list(serial.tools.list_ports.comports())
            
            if not available_ports:
                QMessageBox.warning(
                    self,
                    "No Ports Found",
                    "No serial ports were found on your system.\n\n"
                    "Please check that your device is connected properly."
                )
                return
            
            # Create a list of port names with descriptions
            port_list = []
            for port in available_ports:
                # Format: "COM3 - Silicon Labs CP210x USB to UART Bridge"
                port_desc = f"{port.device} - {port.description}"
                port_list.append(port_desc)
            
            # Show a dialog to select a port
            port_desc, ok = QInputDialog.getItem(
                self,
                "Select Port",
                "Available ports:",
                port_list,
                0,  # Default to first item
                False  # Not editable
            )
            
            if ok and port_desc:
                # Extract the port name from the description (e.g., "COM3 - ..." -> "COM3")
                port = port_desc.split(" - ")[0]
                
                # Log the selected port with details
                for p in available_ports:
                    if p.device == port:
                        logger.info(f"Selected port: {port}, Description: {p.description}, Hardware ID: {p.hwid}")
                        break
                
                # Connect to the selected port
                self._direct_connect_port(port)
        except Exception as e:
            logger.error(f"Error in direct connect dialog: {e}")
            QMessageBox.critical(self, "Error", f"Error in direct connect dialog: {e}")
    
    def _direct_connect_port(self, port):
        """Directly connect to a COM port bypassing device detection"""
        try:
            # Show a dialog to select baud rate with common ESP32 rates highlighted
            baud_rates = ["9600 (Common)", "19200", "38400", "57600", "115200 (ESP32 Default)", "230400", "460800", "921600"]
            baud_rate, ok = QInputDialog.getItem(
                self, "Select Baud Rate",
                f"Select baud rate for connection to {port}:",
                baud_rates, 4, False  # Default to 115200
            )
            
            if ok and baud_rate:
                # Extract the numeric part of the baud rate (remove any descriptive text)
                baud_rate = int(baud_rate.split(" ")[0])
                
                # Log the attempt with detailed information
                logger.info(f"Attempting direct connection to {port} at {baud_rate} baud")
                
                # Show connection attempt in status bar
                self.status_bar.showMessage(f"Connecting to {port} at {baud_rate} baud...", 3000)
                
                # Try to open the connection directly
                if self.app.serial_manager.open_connection(port, baud_rate=baud_rate):
                    self.status_bar.showMessage(f"Connected to {port} at {baud_rate} baud", 5000)
                    
                    # Create a manual device entry if it doesn't exist
                    device = self.app.device_manager.get_device_by_port(port)
                    if not device:
                        device = self.app.device_manager.add_manual_port(port, "esp32", f"ESP32 on {port} (Direct)")
                    
                    # Show success message
                    QMessageBox.information(
                        self,
                        "Connection Successful",
                        f"Successfully connected to {port} at {baud_rate} baud.\n\n"
                        f"You can now use the Serial Monitor to communicate with your device."
                    )
                    
                    # Switch to Serial Monitor tab
                    self.central_widget.setCurrentWidget(self.serial_monitor)
                    
                    return True
                else:
                    # Try with different baud rates as a fallback
                    common_esp32_rates = [115200, 9600, 74880]
                    
                    # Only try other rates if the selected rate wasn't already tried
                    if baud_rate not in common_esp32_rates:
                        common_esp32_rates.insert(0, baud_rate)
                    
                    # Try each baud rate
                    for rate in common_esp32_rates:
                        if rate == baud_rate:
                            continue  # Skip the already tried rate
                            
                        logger.info(f"Trying alternative baud rate: {rate}")
                        self.status_bar.showMessage(f"Trying {port} at {rate} baud...", 1000)
                        
                        if self.app.serial_manager.open_connection(port, baud_rate=rate):
                            self.status_bar.showMessage(f"Connected to {port} at {rate} baud", 5000)
                            
                            # Create a manual device entry if it doesn't exist
                            device = self.app.device_manager.get_device_by_port(port)
                            if not device:
                                device = self.app.device_manager.add_manual_port(port, "esp32", f"ESP32 on {port} (Direct)")
                            
                            QMessageBox.information(
                                self,
                                "Connection Successful",
                                f"Connected to {port} at {rate} baud.\n\n"
                                f"You can now use the Serial Monitor to communicate with your device."
                            )
                            
                            # Switch to Serial Monitor tab
                            self.central_widget.setCurrentWidget(self.serial_monitor)
                            
                            return True
                    
                    # If we get here, all connection attempts failed
                    # Try with different data bits, parity, and stop bits
                    logger.warning(f"Trying alternative serial settings for {port}")
                    self.status_bar.showMessage(f"Trying alternative settings for {port}...", 1000)
                    
                    if self.app.serial_manager.open_connection(port, baud_rate=baud_rate, data_bits=7, parity="E", stop_bits=1):
                        self.status_bar.showMessage(f"Connected to {port} with alternative settings", 5000)
                        
                        # Create a manual device entry if it doesn't exist
                        device = self.app.device_manager.get_device_by_port(port)
                        if not device:
                            device = self.app.device_manager.add_manual_port(port, "esp32", f"ESP32 on {port} (Direct)")
                        
                        QMessageBox.information(
                            self,
                            "Connection Successful",
                            f"Connected to {port} with alternative settings (7E1).\n\n"
                            f"You can now use the Serial Monitor to communicate with your device."
                        )
                        
                        # Switch to Serial Monitor tab
                        self.central_widget.setCurrentWidget(self.serial_monitor)
                        
                        return True
                    else:
                        # All connection attempts failed
                        QMessageBox.warning(
                            self,
                            "Connection Failed",
                            f"Failed to connect to {port} after trying multiple settings.\n\n"
                            f"Please check that:\n"
                            f"1. The port is not in use by another application (like Arduino IDE)\n"
                            f"2. You have permission to access the port\n"
                            f"3. The device is properly connected\n"
                            f"4. The correct drivers are installed\n\n"
                            f"You may need to restart the application or your computer."
                        )
                        return False
        except Exception as e:
            logger.error(f"Error in direct connection: {e}")
            QMessageBox.critical(self, "Error", f"Error connecting directly to {port}: {e}")
            return False
    
    def _reset_layout(self):
        """Reset the window layout to default"""
        try:
            # Reset dock widgets
            self.removeDockWidget(self.device_dock)
            self.removeDockWidget(self.command_dock)
            
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.device_dock)
            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.command_dock)
            
            self.device_dock.setVisible(True)
            self.command_dock.setVisible(True)
            
            # Reset central widget
            self.central_widget.setCurrentIndex(0)
            
            # Update the status bar
            self.status_bar.showMessage("Layout reset to default", 3000)
        except Exception as e:
            logger.error(f"Error resetting layout: {e}")
            QMessageBox.critical(self, "Error", f"Error resetting layout: {e}")
    
    def _show_options(self):
        """Show the options dialog"""
        try:
            # TODO: Implement options dialog
            QMessageBox.information(self, "Options", "Options dialog not implemented yet.")
        except Exception as e:
            logger.error(f"Error showing options: {e}")
            QMessageBox.critical(self, "Error", f"Error showing options: {e}")
    
    def _show_about(self):
        """Show the about dialog"""
        try:
            QMessageBox.about(
                self,
                "About Universal Hardware Debugger",
                f"<h1>Universal Hardware Debugger and Serial Monitor</h1>"
                f"<p>Version {self.app.applicationVersion()}</p>"
                f"<p>A cross-platform application for debugging and monitoring multiple microcontrollers simultaneously.</p>"
                f"<p>Built with Python {platform.python_version()} and PyQt6</p>"
                f"<p>&copy; 2025 Universal Hardware Debugger</p>"
            )
        except Exception as e:
            logger.error(f"Error showing about dialog: {e}")
            QMessageBox.critical(self, "Error", f"Error showing about dialog: {e}")
    
    def _show_documentation(self):
        """Show the documentation"""
        try:
            # TODO: Implement documentation viewer
            QMessageBox.information(self, "Documentation", "Documentation viewer not implemented yet.")
        except Exception as e:
            logger.error(f"Error showing documentation: {e}")
            QMessageBox.critical(self, "Error", f"Error showing documentation: {e}")
    
    def _check_available_ports(self):
        """Check and display available serial ports"""
        try:
            import serial.tools.list_ports
            
            # Get list of available ports
            ports = list(serial.tools.list_ports.comports())
            
            if not ports:
                QMessageBox.information(
                    self,
                    "Available Ports",
                    "No serial ports were found on your system.\n\n"
                    "Please check that your device is connected properly."
                )
                return
            
            # Create a detailed report of available ports
            port_info = "Available Serial Ports:\n\n"
            
            for i, port in enumerate(ports):
                port_info += f"{i+1}. Port: {port.device}\n"
                port_info += f"   Description: {port.description}\n"
                port_info += f"   Hardware ID: {port.hwid}\n"
                
                # Extract VID:PID if available
                vid_pid = f"{port.vid:04X}:{port.pid:04X}" if port.vid and port.pid else "None"
                port_info += f"   VID:PID: {vid_pid}\n"
                
                # Check if this is a known device
                if port.vid and port.pid:
                    vid_pid = f"{port.vid:04X}:{port.pid:04X}"
                    if hasattr(self.app.device_manager, 'KNOWN_DEVICES') and vid_pid in self.app.device_manager.KNOWN_DEVICES:
                        device_info = self.app.device_manager.KNOWN_DEVICES[vid_pid]
                        port_info += f"   Recognized as: {device_info['name']} ({device_info['type']})\n"
                
                port_info += "\n"
            
            # Show the port information in a message box
            QMessageBox.information(
                self,
                "Available Ports",
                port_info
            )
            
            # Log the port information
            logger.info(f"Available ports:\n{port_info}")
        except Exception as e:
            logger.error(f"Error checking available ports: {e}")
            QMessageBox.critical(self, "Error", f"Error checking available ports: {e}")
    
    def _clear_terminal(self):
        """Clear the serial monitor terminal"""
        try:
            self.serial_monitor.clear_terminal()
            self.status_bar.showMessage("Terminal cleared", 3000)
        except Exception as e:
            logger.error(f"Error clearing terminal: {e}")
            QMessageBox.critical(self, "Error", f"Error clearing terminal: {e}")
    
    def get_ui_state(self):
        """Get the current UI state"""
        try:
            return {
                "window_size": [self.width(), self.height()],
                "window_position": [self.x(), self.y()],
                "window_maximized": self.isMaximized(),
                "current_tab": self.central_widget.currentIndex(),
                "device_dock_visible": self.device_dock.isVisible(),
                "command_dock_visible": self.command_dock.isVisible()
            }
        except Exception as e:
            logger.error(f"Error getting UI state: {e}")
            return {}
    
    def restore_ui_state(self, state):
        """Restore the UI state"""
        try:
            # Restore window size and position
            if "window_size" in state:
                self.resize(state["window_size"][0], state["window_size"][1])
            
            if "window_position" in state:
                self.move(state["window_position"][0], state["window_position"][1])
            
            if "window_maximized" in state and state["window_maximized"]:
                self.showMaximized()
            
            # Restore current tab
            if "current_tab" in state:
                self.central_widget.setCurrentIndex(state["current_tab"])
            
            # Restore dock visibility
            if "device_dock_visible" in state:
                self.device_dock.setVisible(state["device_dock_visible"])
            
            if "command_dock_visible" in state:
                self.command_dock.setVisible(state["command_dock_visible"])
            
            logger.info("UI state restored")
        except Exception as e:
            logger.error(f"Error restoring UI state: {e}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        try:
            # Save the window state
            self._save_window_state()
            
            # Save the current session
            self.app.session_manager.save_current_session()
            
            # Disconnect all devices
            self.app.serial_manager.close_all_connections()
            
            # Shutdown the application
            self.app.shutdown()
            
            # Accept the close event
            event.accept()
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")
            event.accept()  # Still close the window