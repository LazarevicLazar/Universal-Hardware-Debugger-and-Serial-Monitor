#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Device panel for displaying and managing connected devices
"""

import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTreeWidget, QTreeWidgetItem, QMenu, QDialog, QFormLayout,
    QComboBox, QLineEdit, QDialogButtonBox, QMessageBox,
    QCheckBox, QGroupBox, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QColor

logger = logging.getLogger(__name__)

class DevicePanel(QWidget):
    """Panel for displaying and managing connected devices"""
    
    # Signals
    device_selected = pyqtSignal(dict)  # device info
    
    def __init__(self, app):
        """Initialize the device panel"""
        super().__init__()
        
        self.app = app
        
        # Initialize UI components
        self._init_ui()
        
        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_device_list)
        self.update_timer.start(2000)  # Update every 2 seconds
    
    def _init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Device tree
        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabels(["Device", "Port", "Status"])
        self.device_tree.setColumnWidth(0, 200)
        self.device_tree.setColumnWidth(1, 100)
        self.device_tree.setColumnWidth(2, 80)
        self.device_tree.setAlternatingRowColors(True)
        self.device_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.device_tree.customContextMenuRequested.connect(self._show_context_menu)
        self.device_tree.itemSelectionChanged.connect(self._device_selected)
        layout.addWidget(self.device_tree)
        
        # Button layout
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)
        
        # Scan button
        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self._scan_devices)
        button_layout.addWidget(self.scan_button)
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._connect_device)
        button_layout.addWidget(self.connect_button)
        
        # Disconnect button
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self._disconnect_device)
        button_layout.addWidget(self.disconnect_button)
        
        # Settings button
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self._show_device_settings)
        button_layout.addWidget(self.settings_button)
        
        # Initial update
        self.update_device_list()
    
    def update_device_list(self):
        """Update the device list"""
        try:
            # Get the list of devices
            devices = self.app.device_manager.get_device_list()
            
            # Remember the currently selected device
            selected_port = None
            if self.device_tree.selectedItems():
                selected_port = self.device_tree.selectedItems()[0].text(1)
            
            # Clear the tree
            self.device_tree.clear()
            
            # Add devices to the tree
            for device in devices:
                item = QTreeWidgetItem(self.device_tree)
                item.setText(0, device["name"])
                item.setText(1, device["port"])
                
                # Set status
                if device["connected"]:
                    item.setText(2, "Connected")
                    item.setForeground(2, QColor("green"))
                else:
                    item.setText(2, "Disconnected")
                    item.setForeground(2, QColor("red"))
                
                # Store the device info in the item
                item.setData(0, Qt.ItemDataRole.UserRole, device)
                
                # Restore selection
                if device["port"] == selected_port:
                    self.device_tree.setCurrentItem(item)
            
            # Update button states
            self._update_button_states()
        except Exception as e:
            logger.error(f"Error updating device list: {e}")
    
    def _update_button_states(self):
        """Update the button states based on selection"""
        # Get the selected device
        selected = self.device_tree.selectedItems()
        
        if selected:
            device = selected[0].data(0, Qt.ItemDataRole.UserRole)
            
            # Enable/disable buttons based on connection status
            self.connect_button.setEnabled(not device["connected"])
            self.disconnect_button.setEnabled(device["connected"])
            self.settings_button.setEnabled(True)
        else:
            # No selection
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(False)
            self.settings_button.setEnabled(False)
    
    def _scan_devices(self):
        """Scan for connected devices"""
        try:
            # Scan for devices
            self.app.device_manager.scan_devices()
            
            # Update the device list
            self.update_device_list()
        except Exception as e:
            logger.error(f"Error scanning for devices: {e}")
            QMessageBox.critical(self, "Error", f"Error scanning for devices: {e}")
    
    def _connect_device(self):
        """Connect to the selected device"""
        try:
            # Get the selected device
            selected = self.device_tree.selectedItems()
            
            if not selected:
                return
            
            device = selected[0].data(0, Qt.ItemDataRole.UserRole)
            
            # Connect to the device
            if self.app.device_manager.connect_device(device):
                logger.info(f"Connected to device: {device['name']} on {device['port']}")
                
                # Update the device list
                self.update_device_list()
            else:
                QMessageBox.warning(self, "Connection Error", f"Failed to connect to {device['name']} on {device['port']}")
        except Exception as e:
            logger.error(f"Error connecting to device: {e}")
            QMessageBox.critical(self, "Error", f"Error connecting to device: {e}")
    
    def _disconnect_device(self):
        """Disconnect from the selected device"""
        try:
            # Get the selected device
            selected = self.device_tree.selectedItems()
            
            if not selected:
                return
            
            device = selected[0].data(0, Qt.ItemDataRole.UserRole)
            
            # Disconnect from the device
            if self.app.device_manager.disconnect_device(device):
                logger.info(f"Disconnected from device: {device['name']} on {device['port']}")
                
                # Update the device list
                self.update_device_list()
            else:
                QMessageBox.warning(self, "Disconnection Error", f"Failed to disconnect from {device['name']} on {device['port']}")
        except Exception as e:
            logger.error(f"Error disconnecting from device: {e}")
            QMessageBox.critical(self, "Error", f"Error disconnecting from device: {e}")
    
    def _show_device_settings(self):
        """Show the device settings dialog"""
        try:
            # Get the selected device
            selected = self.device_tree.selectedItems()
            
            if not selected:
                return
            
            device = selected[0].data(0, Qt.ItemDataRole.UserRole)
            
            # Create and show the settings dialog
            dialog = DeviceSettingsDialog(self.app, device)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Update the device list
                self.update_device_list()
        except Exception as e:
            logger.error(f"Error showing device settings: {e}")
            QMessageBox.critical(self, "Error", f"Error showing device settings: {e}")
    
    def _show_context_menu(self, position):
        """Show the context menu for the device tree"""
        try:
            # Get the selected device
            selected = self.device_tree.selectedItems()
            
            if not selected:
                return
            
            device = selected[0].data(0, Qt.ItemDataRole.UserRole)
            
            # Create the context menu
            menu = QMenu()
            
            # Connect/Disconnect action
            if device["connected"]:
                disconnect_action = QAction("Disconnect", self)
                disconnect_action.triggered.connect(self._disconnect_device)
                menu.addAction(disconnect_action)
            else:
                connect_action = QAction("Connect", self)
                connect_action.triggered.connect(self._connect_device)
                menu.addAction(connect_action)
            
            # Settings action
            settings_action = QAction("Settings", self)
            settings_action.triggered.connect(self._show_device_settings)
            menu.addAction(settings_action)
            
            # Show the menu
            menu.exec(self.device_tree.viewport().mapToGlobal(position))
        except Exception as e:
            logger.error(f"Error showing context menu: {e}")
    
    def _device_selected(self):
        """Handle device selection"""
        try:
            # Get the selected device
            selected = self.device_tree.selectedItems()
            
            if not selected:
                return
            
            device = selected[0].data(0, Qt.ItemDataRole.UserRole)
            
            # Emit the signal
            self.device_selected.emit(device)
            
            # Update button states
            self._update_button_states()
        except Exception as e:
            logger.error(f"Error handling device selection: {e}")


class DeviceSettingsDialog(QDialog):
    """Dialog for configuring device settings"""
    
    def __init__(self, app, device):
        """Initialize the device settings dialog"""
        super().__init__()
        
        self.app = app
        self.device = device
        
        # Set dialog properties
        self.setWindowTitle(f"Device Settings - {device['name']}")
        self.setMinimumWidth(400)
        
        # Initialize UI components
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Connection settings group
        connection_group = QGroupBox("Connection Settings")
        layout.addWidget(connection_group)
        
        connection_layout = QFormLayout()
        connection_group.setLayout(connection_layout)
        
        # Port
        self.port_label = QLabel(self.device["port"])
        connection_layout.addRow("Port:", self.port_label)
        
        # Baud rate
        self.baud_rate_combo = QComboBox()
        for rate in [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]:
            self.baud_rate_combo.addItem(str(rate))
        
        # Set the current baud rate
        current_baud = 115200  # Default
        if self.device["connected"]:
            connection = self.app.serial_manager.get_connection(self.device["port"])
            if connection:
                current_baud = connection.baud_rate
        
        index = self.baud_rate_combo.findText(str(current_baud))
        if index >= 0:
            self.baud_rate_combo.setCurrentIndex(index)
        
        connection_layout.addRow("Baud Rate:", self.baud_rate_combo)
        
        # Data bits
        self.data_bits_combo = QComboBox()
        for bits in [5, 6, 7, 8]:
            self.data_bits_combo.addItem(str(bits))
        
        # Set the current data bits
        current_data_bits = 8  # Default
        if self.device["connected"]:
            connection = self.app.serial_manager.get_connection(self.device["port"])
            if connection:
                current_data_bits = connection.data_bits
        
        index = self.data_bits_combo.findText(str(current_data_bits))
        if index >= 0:
            self.data_bits_combo.setCurrentIndex(index)
        
        connection_layout.addRow("Data Bits:", self.data_bits_combo)
        
        # Parity
        self.parity_combo = QComboBox()
        for parity in [("None", "N"), ("Even", "E"), ("Odd", "O"), ("Mark", "M"), ("Space", "S")]:
            self.parity_combo.addItem(parity[0], parity[1])
        
        # Set the current parity
        current_parity = "N"  # Default
        if self.device["connected"]:
            connection = self.app.serial_manager.get_connection(self.device["port"])
            if connection:
                current_parity = connection.parity
        
        for i in range(self.parity_combo.count()):
            if self.parity_combo.itemData(i) == current_parity:
                self.parity_combo.setCurrentIndex(i)
                break
        
        connection_layout.addRow("Parity:", self.parity_combo)
        
        # Stop bits
        self.stop_bits_combo = QComboBox()
        for bits in [1, 1.5, 2]:
            self.stop_bits_combo.addItem(str(bits))
        
        # Set the current stop bits
        current_stop_bits = 1  # Default
        if self.device["connected"]:
            connection = self.app.serial_manager.get_connection(self.device["port"])
            if connection:
                current_stop_bits = connection.stop_bits
        
        index = self.stop_bits_combo.findText(str(current_stop_bits))
        if index >= 0:
            self.stop_bits_combo.setCurrentIndex(index)
        
        connection_layout.addRow("Stop Bits:", self.stop_bits_combo)
        
        # Flow control
        self.flow_control_combo = QComboBox()
        for flow in [("None", "none"), ("XON/XOFF", "xonxoff"), ("RTS/CTS", "rtscts"), ("DSR/DTR", "dsrdtr")]:
            self.flow_control_combo.addItem(flow[0], flow[1])
        
        # Set the current flow control
        current_flow_control = "none"  # Default
        if self.device["connected"]:
            connection = self.app.serial_manager.get_connection(self.device["port"])
            if connection:
                current_flow_control = connection.flow_control
        
        for i in range(self.flow_control_combo.count()):
            if self.flow_control_combo.itemData(i) == current_flow_control:
                self.flow_control_combo.setCurrentIndex(i)
                break
        
        connection_layout.addRow("Flow Control:", self.flow_control_combo)
        
        # Auto-connect checkbox
        self.auto_connect_check = QCheckBox("Auto-connect on startup")
        self.auto_connect_check.setChecked(self.app.config.get("devices", "auto_connect", True))
        layout.addWidget(self.auto_connect_check)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def accept(self):
        """Handle dialog acceptance"""
        try:
            # Get the settings
            baud_rate = int(self.baud_rate_combo.currentText())
            data_bits = int(self.data_bits_combo.currentText())
            parity = self.parity_combo.currentData()
            stop_bits = float(self.stop_bits_combo.currentText())
            flow_control = self.flow_control_combo.currentData()
            auto_connect = self.auto_connect_check.isChecked()
            
            # Save the auto-connect setting
            self.app.config.set("devices", "auto_connect", auto_connect)
            
            # If the device is connected, update the connection settings
            if self.device["connected"]:
                # Disconnect first
                self.app.device_manager.disconnect_device(self.device)
                
                # Reconnect with new settings
                self.app.serial_manager.open_connection(
                    self.device["port"],
                    baud_rate=baud_rate,
                    data_bits=data_bits,
                    parity=parity,
                    stop_bits=stop_bits,
                    flow_control=flow_control
                )
            
            # Save the settings as defaults for this device type
            if self.device["type"] != "unknown":
                self.app.config.set("devices", f"default_baud_rate_{self.device['type']}", baud_rate)
                self.app.config.set("devices", f"default_data_bits_{self.device['type']}", data_bits)
                self.app.config.set("devices", f"default_parity_{self.device['type']}", parity)
                self.app.config.set("devices", f"default_stop_bits_{self.device['type']}", stop_bits)
                self.app.config.set("devices", f"default_flow_control_{self.device['type']}", flow_control)
            
            # Close the dialog
            super().accept()
        except Exception as e:
            logger.error(f"Error saving device settings: {e}")
            QMessageBox.critical(self, "Error", f"Error saving device settings: {e}")