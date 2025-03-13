#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Serial monitor for displaying and managing serial communication
"""

import logging
import time
import re
import csv
import json
from datetime import datetime
from pathlib import Path
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QComboBox, QCheckBox, QLineEdit, QTabWidget,
    QSplitter, QToolBar, QFileDialog, QMessageBox, QMenu,
    QSpinBox, QGroupBox, QFormLayout, QRadioButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QAction, QIcon, QTextCursor, QColor, QTextCharFormat, QFont

logger = logging.getLogger(__name__)

class SerialMonitor(QWidget):
    """Widget for displaying and managing serial communication"""
    
    def __init__(self, app):
        """Initialize the serial monitor"""
        super().__init__()
        
        self.app = app
        
        # Data storage
        self.log_data = {}  # port -> list of (timestamp, data) tuples
        self.max_log_size = 10000  # Maximum number of lines to keep in memory
        
        # Auto-scroll flag
        self.auto_scroll = True
        
        # Timestamp format
        self.timestamp_format = "%Y-%m-%d %H:%M:%S.%f"
        
        # Initialize UI components
        self._init_ui()
        
        # Connect signals
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Toolbar
        toolbar = QToolBar()
        layout.addWidget(toolbar)
        
        # Clear button
        clear_action = QAction("Clear", self)
        clear_action.triggered.connect(self.clear_terminal)
        toolbar.addAction(clear_action)
        
        # Save button
        save_action = QAction("Save Log", self)
        save_action.triggered.connect(self._save_log)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # Auto-scroll checkbox
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.stateChanged.connect(self._toggle_auto_scroll)
        toolbar.addWidget(self.auto_scroll_check)
        
        # Show timestamps checkbox
        self.show_timestamps_check = QCheckBox("Show Timestamps")
        self.show_timestamps_check.setChecked(True)
        toolbar.addWidget(self.show_timestamps_check)
        
        toolbar.addSeparator()
        
        # Filter label
        filter_label = QLabel("Filter:")
        toolbar.addWidget(filter_label)
        
        # Filter input
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter text...")
        self.filter_input.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self.filter_input)
        
        # Tab widget for multiple devices
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        layout.addWidget(self.tab_widget)
        
        # Add "All Devices" tab
        self.all_devices_tab = QWidget()
        self.tab_widget.addTab(self.all_devices_tab, "All Devices")
        
        all_tab_layout = QVBoxLayout()
        self.all_devices_tab.setLayout(all_tab_layout)
        
        self.all_devices_text = QTextEdit()
        self.all_devices_text.setReadOnly(True)
        self.all_devices_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.all_devices_text.setFont(QFont("Courier New", 10))
        all_tab_layout.addWidget(self.all_devices_text)
    
    def _connect_signals(self):
        """Connect signals from the serial manager"""
        # Connect to the serial manager's signals
        if hasattr(self.app, 'serial_manager'):
            for port, connection in self.app.serial_manager.get_connections().items():
                connection.data_received.connect(self.add_data)
    
    def add_data(self, port, data, timestamp):
        """Add data from a device to the monitor"""
        try:
            # Create a tab for this port if it doesn't exist
            if not self._has_tab_for_port(port):
                self._create_tab_for_port(port)
            
            # Add to the log data
            if port not in self.log_data:
                self.log_data[port] = []
            
            self.log_data[port].append((timestamp, data))
            
            # Trim log data if needed
            if len(self.log_data[port]) > self.max_log_size:
                self.log_data[port] = self.log_data[port][-self.max_log_size:]
            
            # Format the data for display
            display_text = self._format_data_for_display(port, data, timestamp)
            
            # Add to the port-specific tab
            text_edit = self.tab_widget.findChild(QTextEdit, f"text_edit_{port}")
            if text_edit:
                text_edit.append(display_text)
                
                # Auto-scroll if enabled
                if self.auto_scroll:
                    text_edit.moveCursor(QTextCursor.MoveOperation.End)
            
            # Add to the "All Devices" tab
            self.all_devices_text.append(f"[{port}] {display_text}")
            
            # Auto-scroll if enabled
            if self.auto_scroll:
                self.all_devices_text.moveCursor(QTextCursor.MoveOperation.End)
        except Exception as e:
            logger.error(f"Error adding data to monitor: {e}")
    
    def clear_terminal(self):
        """Clear the terminal"""
        try:
            # Clear the "All Devices" tab
            self.all_devices_text.clear()
            
            # Clear all port-specific tabs
            for i in range(1, self.tab_widget.count()):
                text_edit = self.tab_widget.widget(i).findChild(QTextEdit)
                if text_edit:
                    text_edit.clear()
            
            # Clear the log data
            self.log_data = {}
            
            logger.info("Terminal cleared")
        except Exception as e:
            logger.error(f"Error clearing terminal: {e}")
    
    def export_logs(self, file_path, format="txt"):
        """Export logs to a file"""
        try:
            if format == "csv":
                self._export_csv(file_path)
            elif format == "json":
                self._export_json(file_path)
            else:
                self._export_text(file_path)
            
            logger.info(f"Logs exported to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting logs: {e}")
            return False
    
    def _export_csv(self, file_path):
        """Export logs to a CSV file"""
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(["Port", "Timestamp", "Data"])
            
            # Write data
            for port, data_list in self.log_data.items():
                for timestamp, data in data_list:
                    writer.writerow([port, timestamp, data])
    
    def _export_json(self, file_path):
        """Export logs to a JSON file"""
        # Convert log data to a serializable format
        json_data = {}
        
        for port, data_list in self.log_data.items():
            json_data[port] = [{"timestamp": ts, "data": data} for ts, data in data_list]
        
        # Write to file
        with open(file_path, 'w') as f:
            json.dump(json_data, f, indent=2)
    
    def _export_text(self, file_path):
        """Export logs to a text file"""
        with open(file_path, 'w') as f:
            for port, data_list in self.log_data.items():
                for timestamp, data in data_list:
                    f.write(f"[{port}] [{timestamp}] {data}\n")
    
    def _has_tab_for_port(self, port):
        """Check if a tab exists for the given port"""
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == port:
                return True
        return False
    
    def _create_tab_for_port(self, port):
        """Create a new tab for the given port"""
        try:
            # Create a new tab
            tab = QWidget()
            tab_layout = QVBoxLayout()
            tab.setLayout(tab_layout)
            
            # Create a text edit for the tab
            text_edit = QTextEdit()
            text_edit.setObjectName(f"text_edit_{port}")
            text_edit.setReadOnly(True)
            text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
            text_edit.setFont(QFont("Courier New", 10))
            tab_layout.addWidget(text_edit)
            
            # Add the tab
            self.tab_widget.addTab(tab, port)
            
            logger.debug(f"Created tab for port {port}")
        except Exception as e:
            logger.error(f"Error creating tab for port {port}: {e}")
    
    def _close_tab(self, index):
        """Close a tab"""
        try:
            # Don't close the "All Devices" tab
            if index == 0:
                return
            
            # Get the port from the tab text
            port = self.tab_widget.tabText(index)
            
            # Remove the tab
            self.tab_widget.removeTab(index)
            
            logger.debug(f"Closed tab for port {port}")
        except Exception as e:
            logger.error(f"Error closing tab: {e}")
    
    def _format_data_for_display(self, port, data, timestamp):
        """Format data for display in the terminal"""
        # Add timestamp if enabled
        if self.show_timestamps_check.isChecked():
            return f"[{timestamp}] {data}"
        else:
            return data
    
    def _toggle_auto_scroll(self, state):
        """Toggle auto-scrolling"""
        self.auto_scroll = state == Qt.CheckState.Checked
    
    def _apply_filter(self):
        """Apply the filter to the displayed data"""
        try:
            filter_text = self.filter_input.text()
            
            if not filter_text:
                # No filter, show all data
                self._refresh_display()
                return
            
            # Apply filter to all tabs
            for port, data_list in self.log_data.items():
                # Get the text edit for this port
                text_edit = self.tab_widget.findChild(QTextEdit, f"text_edit_{port}")
                
                if text_edit:
                    # Clear the text edit
                    text_edit.clear()
                    
                    # Add only matching lines
                    for timestamp, data in data_list:
                        if filter_text.lower() in data.lower():
                            display_text = self._format_data_for_display(port, data, timestamp)
                            text_edit.append(display_text)
            
            # Apply filter to "All Devices" tab
            self.all_devices_text.clear()
            
            for port, data_list in self.log_data.items():
                for timestamp, data in data_list:
                    if filter_text.lower() in data.lower():
                        display_text = self._format_data_for_display(port, data, timestamp)
                        self.all_devices_text.append(f"[{port}] {display_text}")
        except Exception as e:
            logger.error(f"Error applying filter: {e}")
    
    def _refresh_display(self):
        """Refresh the display with all data"""
        try:
            # Clear all text edits
            self.all_devices_text.clear()
            
            for i in range(1, self.tab_widget.count()):
                text_edit = self.tab_widget.widget(i).findChild(QTextEdit)
                if text_edit:
                    text_edit.clear()
            
            # Re-add all data
            for port, data_list in self.log_data.items():
                # Get the text edit for this port
                text_edit = self.tab_widget.findChild(QTextEdit, f"text_edit_{port}")
                
                for timestamp, data in data_list:
                    display_text = self._format_data_for_display(port, data, timestamp)
                    
                    # Add to port-specific tab
                    if text_edit:
                        text_edit.append(display_text)
                    
                    # Add to "All Devices" tab
                    self.all_devices_text.append(f"[{port}] {display_text}")
        except Exception as e:
            logger.error(f"Error refreshing display: {e}")
    
    def _save_log(self):
        """Save the log to a file"""
        try:
            # Show a file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Log", "", "Text Files (*.txt);;CSV Files (*.csv);;JSON Files (*.json)"
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
            if self.export_logs(file_path, format):
                QMessageBox.information(self, "Save Log", f"Log saved to {file_path}")
            else:
                QMessageBox.warning(self, "Save Log", "Error saving log")
        except Exception as e:
            logger.error(f"Error saving log: {e}")
            QMessageBox.critical(self, "Error", f"Error saving log: {e}")