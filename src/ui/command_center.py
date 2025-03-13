#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Command center for sending commands to devices
"""

import logging
import time
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QComboBox, QCheckBox, QLineEdit, QTabWidget,
    QSplitter, QToolBar, QFileDialog, QMessageBox, QMenu,
    QSpinBox, QGroupBox, QFormLayout, QListWidget, QListWidgetItem,
    QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QAction, QIcon, QTextCursor, QColor, QTextCharFormat, QFont

logger = logging.getLogger(__name__)

class CommandCenter(QWidget):
    """Widget for sending commands to devices"""
    
    def __init__(self, app):
        """Initialize the command center"""
        super().__init__()
        
        self.app = app
        
        # Initialize UI components
        self._init_ui()
        
        # Connect signals
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create a splitter for command input and history/favorites
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left side - Command input
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        # Device selection
        device_layout = QHBoxLayout()
        left_layout.addLayout(device_layout)
        
        device_layout.addWidget(QLabel("Device:"))
        
        self.device_combo = QComboBox()
        self.device_combo.addItem("All Devices", "broadcast")
        device_layout.addWidget(self.device_combo)
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_devices)
        device_layout.addWidget(refresh_button)
        
        # Command input
        left_layout.addWidget(QLabel("Command:"))
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command...")
        self.command_input.returnPressed.connect(self._send_command)
        left_layout.addWidget(self.command_input)
        
        # Options
        options_layout = QHBoxLayout()
        left_layout.addLayout(options_layout)
        
        # Add newline checkbox
        self.add_newline_check = QCheckBox("Add newline")
        self.add_newline_check.setChecked(True)
        options_layout.addWidget(self.add_newline_check)
        
        # Hex mode checkbox
        self.hex_mode_check = QCheckBox("Hex mode")
        self.hex_mode_check.setChecked(False)
        options_layout.addWidget(self.hex_mode_check)
        
        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self._send_command)
        options_layout.addWidget(self.send_button)
        
        # Schedule button
        self.schedule_button = QPushButton("Schedule")
        self.schedule_button.clicked.connect(self._schedule_command)
        options_layout.addWidget(self.schedule_button)
        
        # Right side - Tabs for history, favorites, macros, scheduled
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        right_layout.addWidget(self.tab_widget)
        
        # History tab
        self.history_tab = QWidget()
        history_layout = QVBoxLayout()
        self.history_tab.setLayout(history_layout)
        
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self._use_history_item)
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self._show_history_context_menu)
        history_layout.addWidget(self.history_list)
        
        history_button_layout = QHBoxLayout()
        history_layout.addLayout(history_button_layout)
        
        clear_history_button = QPushButton("Clear History")
        clear_history_button.clicked.connect(self._clear_history)
        history_button_layout.addWidget(clear_history_button)
        
        self.tab_widget.addTab(self.history_tab, "History")
        
        # Favorites tab
        self.favorites_tab = QWidget()
        favorites_layout = QVBoxLayout()
        self.favorites_tab.setLayout(favorites_layout)
        
        self.favorites_list = QListWidget()
        self.favorites_list.itemDoubleClicked.connect(self._use_favorite_item)
        self.favorites_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.favorites_list.customContextMenuRequested.connect(self._show_favorites_context_menu)
        favorites_layout.addWidget(self.favorites_list)
        
        favorites_button_layout = QHBoxLayout()
        favorites_layout.addLayout(favorites_button_layout)
        
        add_favorite_button = QPushButton("Add Current")
        add_favorite_button.clicked.connect(self._add_favorite)
        favorites_button_layout.addWidget(add_favorite_button)
        
        self.tab_widget.addTab(self.favorites_tab, "Favorites")
        
        # Macros tab
        self.macros_tab = QWidget()
        macros_layout = QVBoxLayout()
        self.macros_tab.setLayout(macros_layout)
        
        self.macros_list = QListWidget()
        self.macros_list.itemDoubleClicked.connect(self._use_macro)
        self.macros_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.macros_list.customContextMenuRequested.connect(self._show_macros_context_menu)
        macros_layout.addWidget(self.macros_list)
        
        macros_button_layout = QHBoxLayout()
        macros_layout.addLayout(macros_button_layout)
        
        create_macro_button = QPushButton("Create Macro")
        create_macro_button.clicked.connect(self._create_macro)
        macros_button_layout.addWidget(create_macro_button)
        
        self.tab_widget.addTab(self.macros_tab, "Macros")
        
        # Scheduled tab
        self.scheduled_tab = QWidget()
        scheduled_layout = QVBoxLayout()
        self.scheduled_tab.setLayout(scheduled_layout)
        
        self.scheduled_table = QTableWidget()
        self.scheduled_table.setColumnCount(4)
        self.scheduled_table.setHorizontalHeaderLabels(["Device", "Command", "Time", "Repeat"])
        self.scheduled_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.scheduled_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.scheduled_table.customContextMenuRequested.connect(self._show_scheduled_context_menu)
        scheduled_layout.addWidget(self.scheduled_table)
        
        self.tab_widget.addTab(self.scheduled_tab, "Scheduled")
        
        # Set the splitter sizes
        splitter.setSizes([500, 300])
        
        # Update the UI
        self._refresh_devices()
        self._refresh_history()
        self._refresh_favorites()
        self._refresh_macros()
        self._refresh_scheduled()
    
    def _connect_signals(self):
        """Connect signals"""
        # Connect to the command interface's signals
        if hasattr(self.app, 'command_interface'):
            self.app.command_interface.command_sent.connect(self._on_command_sent)
            self.app.command_interface.command_scheduled.connect(self._on_command_scheduled)
            self.app.command_interface.command_executed.connect(self._on_command_executed)
    
    def _refresh_devices(self):
        """Refresh the device list"""
        try:
            # Remember the current selection
            current_data = self.device_combo.currentData()
            
            # Clear the combo box
            self.device_combo.clear()
            
            # Add the "All Devices" option
            self.device_combo.addItem("All Devices", "broadcast")
            
            # Add connected devices
            if hasattr(self.app, 'device_manager'):
                for device in self.app.device_manager.get_connected_devices():
                    self.device_combo.addItem(f"{device['name']} ({device['port']})", device['port'])
            
            # Restore the selection if possible
            if current_data:
                index = self.device_combo.findData(current_data)
                if index >= 0:
                    self.device_combo.setCurrentIndex(index)
        except Exception as e:
            logger.error(f"Error refreshing devices: {e}")
    
    def _refresh_history(self):
        """Refresh the command history list"""
        try:
            # Clear the list
            self.history_list.clear()
            
            # Add history items
            if hasattr(self.app, 'command_interface'):
                for entry in reversed(self.app.command_interface.get_history()):
                    item = QListWidgetItem(f"{entry['command']} ({entry['port']})")
                    item.setData(Qt.ItemDataRole.UserRole, entry)
                    self.history_list.addItem(item)
        except Exception as e:
            logger.error(f"Error refreshing history: {e}")
    
    def _refresh_favorites(self):
        """Refresh the favorites list"""
        try:
            # Clear the list
            self.favorites_list.clear()
            
            # Add favorites
            if hasattr(self.app, 'command_interface'):
                for i, favorite in enumerate(self.app.command_interface.get_favorites()):
                    item = QListWidgetItem(favorite['command'])
                    if favorite.get('description'):
                        item.setToolTip(favorite['description'])
                    item.setData(Qt.ItemDataRole.UserRole, (i, favorite))
                    self.favorites_list.addItem(item)
        except Exception as e:
            logger.error(f"Error refreshing favorites: {e}")
    
    def _refresh_macros(self):
        """Refresh the macros list"""
        try:
            # Clear the list
            self.macros_list.clear()
            
            # Add macros
            if hasattr(self.app, 'command_interface'):
                for name, macro in self.app.command_interface.get_macros().items():
                    item = QListWidgetItem(name)
                    if macro.get('description'):
                        item.setToolTip(macro['description'])
                    item.setData(Qt.ItemDataRole.UserRole, macro)
                    self.macros_list.addItem(item)
        except Exception as e:
            logger.error(f"Error refreshing macros: {e}")
    
    def _refresh_scheduled(self):
        """Refresh the scheduled commands table"""
        try:
            # Clear the table
            self.scheduled_table.setRowCount(0)
            
            # Add scheduled commands
            if hasattr(self.app, 'command_interface'):
                for i, command in enumerate(self.app.command_interface.get_scheduled_commands()):
                    row = self.scheduled_table.rowCount()
                    self.scheduled_table.insertRow(row)
                    
                    # Device
                    self.scheduled_table.setItem(row, 0, QTableWidgetItem(command['port']))
                    
                    # Command
                    self.scheduled_table.setItem(row, 1, QTableWidgetItem(command['command']))
                    
                    # Time
                    time_str = command['next_execution'].strftime("%Y-%m-%d %H:%M:%S")
                    self.scheduled_table.setItem(row, 2, QTableWidgetItem(time_str))
                    
                    # Repeat
                    repeat_str = f"Every {command['repeat_interval']}s" if command['repeat'] else "No"
                    self.scheduled_table.setItem(row, 3, QTableWidgetItem(repeat_str))
                    
                    # Store the command index
                    for col in range(4):
                        self.scheduled_table.item(row, col).setData(Qt.ItemDataRole.UserRole, i)
        except Exception as e:
            logger.error(f"Error refreshing scheduled commands: {e}")
    
    def _send_command(self):
        """Send the current command"""
        try:
            # Get the command
            command = self.command_input.text().strip()
            
            if not command:
                return
            
            # Get the device
            device = self.device_combo.currentData()
            
            # Check if hex mode is enabled
            if self.hex_mode_check.isChecked():
                # Convert to hex format
                command = "\\x" + "\\x".join(f"{ord(c):02x}" for c in command)
            
            # Send the command
            add_newline = self.add_newline_check.isChecked()
            
            if device == "broadcast":
                success = self.app.command_interface.broadcast_command(command, add_newline)
            else:
                success = self.app.command_interface.send_command(device, command, add_newline)
            
            if success:
                # Clear the input
                self.command_input.clear()
                
                # Refresh the history
                self._refresh_history()
            else:
                QMessageBox.warning(self, "Send Command", "Failed to send command")
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            QMessageBox.critical(self, "Error", f"Error sending command: {e}")
    
    def _schedule_command(self):
        """Schedule the current command"""
        try:
            # Get the command
            command = self.command_input.text().strip()
            
            if not command:
                return
            
            # Get the device
            device = self.device_combo.currentData()
            
            # Show the schedule dialog
            dialog = ScheduleCommandDialog(self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get the schedule settings
                delay = dialog.get_delay()
                repeat = dialog.get_repeat()
                interval = dialog.get_interval()
                
                # Schedule the command
                if self.app.command_interface.schedule_command(device, command, delay, repeat, interval):
                    # Refresh the scheduled commands
                    self._refresh_scheduled()
                    
                    # Switch to the scheduled tab
                    self.tab_widget.setCurrentWidget(self.scheduled_tab)
                else:
                    QMessageBox.warning(self, "Schedule Command", "Failed to schedule command")
        except Exception as e:
            logger.error(f"Error scheduling command: {e}")
            QMessageBox.critical(self, "Error", f"Error scheduling command: {e}")
    
    def _use_history_item(self, item):
        """Use a command from the history"""
        try:
            # Get the command
            entry = item.data(Qt.ItemDataRole.UserRole)
            
            # Set the command input
            self.command_input.setText(entry['command'])
            
            # Set the device if it's available
            if entry['port'] != "broadcast":
                index = self.device_combo.findData(entry['port'])
                if index >= 0:
                    self.device_combo.setCurrentIndex(index)
        except Exception as e:
            logger.error(f"Error using history item: {e}")
    
    def _use_favorite_item(self, item):
        """Use a favorite command"""
        try:
            # Get the favorite
            _, favorite = item.data(Qt.ItemDataRole.UserRole)
            
            # Set the command input
            self.command_input.setText(favorite['command'])
        except Exception as e:
            logger.error(f"Error using favorite item: {e}")
    
    def _use_macro(self, item):
        """Use a macro"""
        try:
            # Get the macro
            macro = item.data(Qt.ItemDataRole.UserRole)
            
            # Get the device
            device = self.device_combo.currentData()
            
            # Execute the macro
            if self.app.command_interface.execute_macro(macro['name'], device):
                logger.info(f"Macro executed: {macro['name']}")
            else:
                QMessageBox.warning(self, "Execute Macro", f"Failed to execute macro: {macro['name']}")
        except Exception as e:
            logger.error(f"Error using macro: {e}")
            QMessageBox.critical(self, "Error", f"Error using macro: {e}")
    
    def _clear_history(self):
        """Clear the command history"""
        try:
            # Confirm with the user
            reply = QMessageBox.question(
                self, "Clear History",
                "Are you sure you want to clear the command history?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Clear the history
                self.app.command_interface.clear_history()
                
                # Refresh the history
                self._refresh_history()
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            QMessageBox.critical(self, "Error", f"Error clearing history: {e}")
    
    def _add_favorite(self):
        """Add the current command to favorites"""
        try:
            # Get the command
            command = self.command_input.text().strip()
            
            if not command:
                QMessageBox.warning(self, "Add Favorite", "No command to add")
                return
            
            # Show the add favorite dialog
            dialog = AddFavoriteDialog(self, command)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get the description
                description = dialog.get_description()
                
                # Add to favorites
                if self.app.command_interface.add_to_favorites(command, description):
                    # Refresh the favorites
                    self._refresh_favorites()
                    
                    # Switch to the favorites tab
                    self.tab_widget.setCurrentWidget(self.favorites_tab)
                else:
                    QMessageBox.warning(self, "Add Favorite", "Failed to add command to favorites")
        except Exception as e:
            logger.error(f"Error adding favorite: {e}")
            QMessageBox.critical(self, "Error", f"Error adding favorite: {e}")
    
    def _create_macro(self):
        """Create a new macro"""
        try:
            # Show the create macro dialog
            dialog = CreateMacroDialog(self, self.app.command_interface)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Refresh the macros
                self._refresh_macros()
                
                # Switch to the macros tab
                self.tab_widget.setCurrentWidget(self.macros_tab)
        except Exception as e:
            logger.error(f"Error creating macro: {e}")
            QMessageBox.critical(self, "Error", f"Error creating macro: {e}")
    
    def _show_history_context_menu(self, position):
        """Show the context menu for the history list"""
        try:
            # Get the selected item
            item = self.history_list.itemAt(position)
            
            if not item:
                return
            
            # Create the menu
            menu = QMenu()
            
            # Use command action
            use_action = QAction("Use Command", self)
            use_action.triggered.connect(lambda: self._use_history_item(item))
            menu.addAction(use_action)
            
            # Add to favorites action
            add_favorite_action = QAction("Add to Favorites", self)
            add_favorite_action.triggered.connect(lambda: self._add_to_favorites_from_history(item))
            menu.addAction(add_favorite_action)
            
            # Show the menu
            menu.exec(self.history_list.viewport().mapToGlobal(position))
        except Exception as e:
            logger.error(f"Error showing history context menu: {e}")
    
    def _show_favorites_context_menu(self, position):
        """Show the context menu for the favorites list"""
        try:
            # Get the selected item
            item = self.favorites_list.itemAt(position)
            
            if not item:
                return
            
            # Create the menu
            menu = QMenu()
            
            # Use command action
            use_action = QAction("Use Command", self)
            use_action.triggered.connect(lambda: self._use_favorite_item(item))
            menu.addAction(use_action)
            
            # Remove from favorites action
            remove_action = QAction("Remove from Favorites", self)
            remove_action.triggered.connect(lambda: self._remove_from_favorites(item))
            menu.addAction(remove_action)
            
            # Show the menu
            menu.exec(self.favorites_list.viewport().mapToGlobal(position))
        except Exception as e:
            logger.error(f"Error showing favorites context menu: {e}")
    
    def _show_macros_context_menu(self, position):
        """Show the context menu for the macros list"""
        try:
            # Get the selected item
            item = self.macros_list.itemAt(position)
            
            if not item:
                return
            
            # Create the menu
            menu = QMenu()
            
            # Execute macro action
            execute_action = QAction("Execute Macro", self)
            execute_action.triggered.connect(lambda: self._use_macro(item))
            menu.addAction(execute_action)
            
            # Edit macro action
            edit_action = QAction("Edit Macro", self)
            edit_action.triggered.connect(lambda: self._edit_macro(item))
            menu.addAction(edit_action)
            
            # Delete macro action
            delete_action = QAction("Delete Macro", self)
            delete_action.triggered.connect(lambda: self._delete_macro(item))
            menu.addAction(delete_action)
            
            # Show the menu
            menu.exec(self.macros_list.viewport().mapToGlobal(position))
        except Exception as e:
            logger.error(f"Error showing macros context menu: {e}")
    
    def _show_scheduled_context_menu(self, position):
        """Show the context menu for the scheduled commands table"""
        try:
            # Get the selected item
            item = self.scheduled_table.itemAt(position)
            
            if not item:
                return
            
            # Create the menu
            menu = QMenu()
            
            # Cancel command action
            cancel_action = QAction("Cancel Command", self)
            cancel_action.triggered.connect(lambda: self._cancel_scheduled_command(item))
            menu.addAction(cancel_action)
            
            # Show the menu
            menu.exec(self.scheduled_table.viewport().mapToGlobal(position))
        except Exception as e:
            logger.error(f"Error showing scheduled context menu: {e}")
    
    def _add_to_favorites_from_history(self, item):
        """Add a command from history to favorites"""
        try:
            # Get the command
            entry = item.data(Qt.ItemDataRole.UserRole)
            
            # Show the add favorite dialog
            dialog = AddFavoriteDialog(self, entry['command'])
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get the description
                description = dialog.get_description()
                
                # Add to favorites
                if self.app.command_interface.add_to_favorites(entry['command'], description):
                    # Refresh the favorites
                    self._refresh_favorites()
                    
                    # Switch to the favorites tab
                    self.tab_widget.setCurrentWidget(self.favorites_tab)
                else:
                    QMessageBox.warning(self, "Add Favorite", "Failed to add command to favorites")
        except Exception as e:
            logger.error(f"Error adding to favorites from history: {e}")
            QMessageBox.critical(self, "Error", f"Error adding to favorites: {e}")
    
    def _remove_from_favorites(self, item):
        """Remove a command from favorites"""
        try:
            # Get the favorite index
            index, _ = item.data(Qt.ItemDataRole.UserRole)
            
            # Remove from favorites
            if self.app.command_interface.remove_from_favorites(index):
                # Refresh the favorites
                self._refresh_favorites()
            else:
                QMessageBox.warning(self, "Remove Favorite", "Failed to remove command from favorites")
        except Exception as e:
            logger.error(f"Error removing from favorites: {e}")
            QMessageBox.critical(self, "Error", f"Error removing from favorites: {e}")
    
    def _edit_macro(self, item):
        """Edit a macro"""
        try:
            # Get the macro
            macro = item.data(Qt.ItemDataRole.UserRole)
            
            # Show the edit macro dialog
            dialog = EditMacroDialog(self, self.app.command_interface, macro)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Refresh the macros
                self._refresh_macros()
            
        except Exception as e:
            logger.error(f"Error editing macro: {e}")
            QMessageBox.critical(self, "Error", f"Error editing macro: {e}")
    
    def _delete_macro(self, item):
        """Delete a macro"""
        try:
            # Get the macro
            macro = item.data(Qt.ItemDataRole.UserRole)
            
            # Confirm with the user
            reply = QMessageBox.question(
                self, "Delete Macro",
                f"Are you sure you want to delete the macro '{macro['name']}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Delete the macro
                if self.app.command_interface.delete_macro(macro['name']):
                    # Refresh the macros
                    self._refresh_macros()
                else:
                    QMessageBox.warning(self, "Delete Macro", "Failed to delete macro")
        except Exception as e:
            logger.error(f"Error deleting macro: {e}")
            QMessageBox.critical(self, "Error", f"Error deleting macro: {e}")
    
    def _cancel_scheduled_command(self, item):
        """Cancel a scheduled command"""
        try:
            # Get the command index
            index = item.data(Qt.ItemDataRole.UserRole)
            
            # Cancel the command
            if self.app.command_interface.cancel_scheduled_command(index):
                # Refresh the scheduled commands
                self._refresh_scheduled()
            else:
                QMessageBox.warning(self, "Cancel Command", "Failed to cancel command")
        except Exception as e:
            logger.error(f"Error canceling scheduled command: {e}")
            QMessageBox.critical(self, "Error", f"Error canceling scheduled command: {e}")
    
    def _on_command_sent(self, port, command):
        """Handle command sent signal"""
        # Refresh the history
        self._refresh_history()
    
    def _on_command_scheduled(self, port, command, scheduled_time):
        """Handle command scheduled signal"""
        # Refresh the scheduled commands
        self._refresh_scheduled()
    
    def _on_command_executed(self, port, command, success):
        """Handle command executed signal"""
        # Update the status bar
        if hasattr(self.app, 'main_window'):
            if success:
                self.app.main_window.statusBar().showMessage(f"Command executed: {command}", 3000)
            else:
                self.app.main_window.statusBar().showMessage(f"Command failed: {command}", 3000)


class AddFavoriteDialog(QDialog):
    """Dialog for adding a command to favorites"""
    
    def __init__(self, parent, command):
        """Initialize the dialog"""
        super().__init__(parent)
        
        self.command = command
        
        # Set dialog properties
        self.setWindowTitle("Add to Favorites")
        self.setMinimumWidth(400)
        
        # Initialize UI components
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Command
        layout.addWidget(QLabel("Command:"))
        command_label = QLabel(self.command)
        command_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(command_label)
        
        # Description
        layout.addWidget(QLabel("Description:"))
        self.description_input = QLineEdit()
        layout.addWidget(self.description_input)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_description(self):
        """Get the description"""
        return self.description_input.text()


class ScheduleCommandDialog(QDialog):
    """Dialog for scheduling a command"""
    
    def __init__(self, parent):
        """Initialize the dialog"""
        super().__init__(parent)
        
        # Set dialog properties
        self.setWindowTitle("Schedule Command")
        self.setMinimumWidth(400)
        
        # Initialize UI components
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Delay
        delay_group = QGroupBox("Delay")
        layout.addWidget(delay_group)
        
        delay_layout = QHBoxLayout()
        delay_group.setLayout(delay_layout)
        
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 3600)
        self.delay_spin.setValue(0)
        self.delay_spin.setSuffix(" seconds")
        delay_layout.addWidget(self.delay_spin)
        
        # Repeat
        repeat_group = QGroupBox("Repeat")
        layout.addWidget(repeat_group)
        
        repeat_layout = QVBoxLayout()
        repeat_group.setLayout(repeat_layout)
        
        self.repeat_button_group = QButtonGroup(self)
        
        self.no_repeat_radio = QRadioButton("No repeat")
        self.no_repeat_radio.setChecked(True)
        self.repeat_button_group.addButton(self.no_repeat_radio)
        repeat_layout.addWidget(self.no_repeat_radio)
        
        self.repeat_radio = QRadioButton("Repeat every:")
        self.repeat_button_group.addButton(self.repeat_radio)
        repeat_layout.addWidget(self.repeat_radio)
        
        interval_layout = QHBoxLayout()
        repeat_layout.addLayout(interval_layout)
        
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 3600)
        self.interval_spin.setValue(60)
        self.interval_spin.setSuffix(" seconds")
        self.interval_spin.setEnabled(False)
        interval_layout.addWidget(self.interval_spin)
        
        # Connect signals
        self.repeat_radio.toggled.connect(self._toggle_repeat)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _toggle_repeat(self, checked):
        """Toggle the repeat interval spin box"""
        self.interval_spin.setEnabled(checked)
    
    def get_delay(self):
        """Get the delay in seconds"""
        return self.delay_spin.value()
    
    def get_repeat(self):
        """Get whether to repeat the command"""
        return self.repeat_radio.isChecked()
    
    def get_interval(self):
        """Get the repeat interval in seconds"""
        return self.interval_spin.value()


class CreateMacroDialog(QDialog):
    """Dialog for creating a macro"""
    
    def __init__(self, parent, command_interface):
        """Initialize the dialog"""
        super().__init__(parent)
        
        self.command_interface = command_interface
        
        # Set dialog properties
        self.setWindowTitle("Create Macro")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Initialize UI components
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Macro name
        name_layout = QHBoxLayout()
        layout.addLayout(name_layout)
        
        name_layout.addWidget(QLabel("Name:"))
        
        self.name_input = QLineEdit()
        name_layout.addWidget(self.name_input)
        
        # Description
        desc_layout = QHBoxLayout()
        layout.addLayout(desc_layout)
        
        desc_layout.addWidget(QLabel("Description:"))
        
        self.desc_input = QLineEdit()
        desc_layout.addWidget(self.desc_input)
        
        # Commands
        layout.addWidget(QLabel("Commands:"))
        
        self.commands_list = QListWidget()
        layout.addWidget(self.commands_list)
        
        # Command input
        cmd_layout = QHBoxLayout()
        layout.addLayout(cmd_layout)
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command...")
        cmd_layout.addWidget(self.command_input)
        
        add_button = QPushButton("Add")
        add_button.clicked.connect(self._add_command)
        cmd_layout.addWidget(add_button)
        
        # Delay input
        delay_layout = QHBoxLayout()
        layout.addLayout(delay_layout)
        
        delay_layout.addWidget(QLabel("Add delay:"))
        
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 60)
        self.delay_spin.setValue(1)
        self.delay_spin.setSuffix(" seconds")
        delay_layout.addWidget(self.delay_spin)
        
        add_delay_button = QPushButton("Add Delay")
        add_delay_button.clicked.connect(self._add_delay)
        delay_layout.addWidget(add_delay_button)
        
        # Button layout
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)
        
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self._remove_command)
        button_layout.addWidget(remove_button)
        
        move_up_button = QPushButton("Move Up")
        move_up_button.clicked.connect(self._move_up)
        button_layout.addWidget(move_up_button)
        
        move_down_button = QPushButton("Move Down")
        move_down_button.clicked.connect(self._move_down)
        button_layout.addWidget(move_down_button)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._create_macro)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _add_command(self):
        """Add a command to the list"""
        command = self.command_input.text().strip()
        
        if command:
            self.commands_list.addItem(command)
            self.command_input.clear()
    
    def _add_delay(self):
        """Add a delay to the list"""
        delay = self.delay_spin.value()
        self.commands_list.addItem(f"DELAY:{delay}")
    
    def _remove_command(self):
        """Remove the selected command"""
        selected = self.commands_list.selectedItems()
        
        if selected:
            for item in selected:
                self.commands_list.takeItem(self.commands_list.row(item))
    
    def _move_up(self):
        """Move the selected command up"""
        selected = self.commands_list.selectedItems()
        
        if selected:
            for item in selected:
                row = self.commands_list.row(item)
                
                if row > 0:
                    self.commands_list.takeItem(row)
                    self.commands_list.insertItem(row - 1, item)
                    self.commands_list.setCurrentItem(item)
    
    def _move_down(self):
        """Move the selected command down"""
        selected = self.commands_list.selectedItems()
        
        if selected:
            for item in selected:
                row = self.commands_list.row(item)
                
                if row < self.commands_list.count() - 1:
                    self.commands_list.takeItem(row)
                    self.commands_list.insertItem(row + 1, item)
                    self.commands_list.setCurrentItem(item)
    
    def _create_macro(self):
        """Create the macro"""
        name = self.name_input.text().strip()
        description = self.desc_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Create Macro", "Please enter a name for the macro")
            return
        
        if self.commands_list.count() == 0:
            QMessageBox.warning(self, "Create Macro", "Please add at least one command to the macro")
            return
        
        # Get the commands
        commands = []
        for i in range(self.commands_list.count()):
            commands.append(self.commands_list.item(i).text())
        
        # Create the macro
        if self.command_interface.create_macro(name, commands, description):
            self.accept()
        else:
            QMessageBox.warning(self, "Create Macro", "Failed to create macro")


class EditMacroDialog(QDialog):
    """Dialog for editing a macro"""
    
    def __init__(self, parent, command_interface, macro):
        """Initialize the dialog"""
        super().__init__(parent)
        
        self.command_interface = command_interface
        self.macro = macro
        
        # Set dialog properties
        self.setWindowTitle(f"Edit Macro: {macro['name']}")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Initialize UI components
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Macro name
        name_layout = QHBoxLayout()
        layout.addLayout(name_layout)
        
        name_layout.addWidget(QLabel("Name:"))
        
        self.name_input = QLineEdit(self.macro['name'])
        self.name_input.setReadOnly(True)  # Can't change the name
        name_layout.addWidget(self.name_input)
        
        # Description
        desc_layout = QHBoxLayout()
        layout.addLayout(desc_layout)
        
        desc_layout.addWidget(QLabel("Description:"))
        
        self.desc_input = QLineEdit(self.macro.get('description', ''))
        desc_layout.addWidget(self.desc_input)
        
        # Commands
        layout.addWidget(QLabel("Commands:"))
        
        self.commands_list = QListWidget()
        layout.addWidget(self.commands_list)
        
        # Add existing commands
        for command in self.macro['commands']:
            self.commands_list.addItem(command)
        
        # Command input
        cmd_layout = QHBoxLayout()
        layout.addLayout(cmd_layout)
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command...")
        cmd_layout.addWidget(self.command_input)
        
        add_button = QPushButton("Add")
        add_button.clicked.connect(self._add_command)
        cmd_layout.addWidget(add_button)
        
        # Delay input
        delay_layout = QHBoxLayout()
        layout.addLayout(delay_layout)
        
        delay_layout.addWidget(QLabel("Add delay:"))
        
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 60)
        self.delay_spin.setValue(1)
        self.delay_spin.setSuffix(" seconds")
        delay_layout.addWidget(self.delay_spin)
        
        add_delay_button = QPushButton("Add Delay")
        add_delay_button.clicked.connect(self._add_delay)
        delay_layout.addWidget(add_delay_button)
        
        # Button layout
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)
        
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self._remove_command)
        button_layout.addWidget(remove_button)
        
        move_up_button = QPushButton("Move Up")
        move_up_button.clicked.connect(self._move_up)
        button_layout.addWidget(move_up_button)
        
        move_down_button = QPushButton("Move Down")
        move_down_button.clicked.connect(self._move_down)
        button_layout.addWidget(move_down_button)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._update_macro)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _add_command(self):
        """Add a command to the list"""
        command = self.command_input.text().strip()
        
        if command:
            self.commands_list.addItem(command)
            self.command_input.clear()
    
    def _add_delay(self):
        """Add a delay to the list"""
        delay = self.delay_spin.value()
        self.commands_list.addItem(f"DELAY:{delay}")
    
    def _remove_command(self):
        """Remove the selected command"""
        selected = self.commands_list.selectedItems()
        
        if selected:
            for item in selected:
                self.commands_list.takeItem(self.commands_list.row(item))
    
    def _move_up(self):
        """Move the selected command up"""
        selected = self.commands_list.selectedItems()
        
        if selected:
            for item in selected:
                row = self.commands_list.row(item)
                
                if row > 0:
                    self.commands_list.takeItem(row)
                    self.commands_list.insertItem(row - 1, item)
                    self.commands_list.setCurrentItem(item)
    
    def _move_down(self):
        """Move the selected command down"""
        selected = self.commands_list.selectedItems()
        
        if selected:
            for item in selected:
                row = self.commands_list.row(item)
                
                if row < self.commands_list.count() - 1:
                    self.commands_list.takeItem(row)
                    self.commands_list.insertItem(row + 1, item)
                    self.commands_list.setCurrentItem(item)
    
    def _update_macro(self):
        """Update the macro"""
        description = self.desc_input.text().strip()
        
        if self.commands_list.count() == 0:
            QMessageBox.warning(self, "Update Macro", "Please add at least one command to the macro")
            return
        
        # Get the commands
        commands = []
        for i in range(self.commands_list.count()):
            commands.append(self.commands_list.item(i).text())
        
        # Update the macro
        if self.command_interface.update_macro(self.macro['name'], commands, description):
            self.accept()
        else:
            QMessageBox.warning(self, "Update Macro", "Failed to update macro")
