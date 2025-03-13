#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Core application class
"""

import sys
import logging
import platform
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QSettings, QTimer

# Theme support removed - using default Qt theme only

from src.core.config import Config
from src.core.session import SessionManager
from src.ui.main_window import MainWindow
from src.devices.manager import DeviceManager
from src.serial.connection import SerialConnectionManager

logger = logging.getLogger(__name__)

class Application(QApplication):
    """Main application class for the Universal Hardware Debugger and Serial Monitor"""
    
    def __init__(self, argv):
        """Initialize the application"""
        super().__init__(argv)
        
        self.setApplicationName("Universal Hardware Debugger")
        self.setApplicationVersion("0.1.0")
        self.setOrganizationName("Universal Hardware Debugger")
        self.setOrganizationDomain("universalhardwaredebugger.org")
        
        # Set up exception handling
        sys.excepthook = self.handle_exception
        
        # Initialize configuration
        self.config = Config()
        
        # Apply theme
        self.apply_theme()
        
        # Initialize managers
        self.session_manager = SessionManager(self)
        self.device_manager = DeviceManager(self)
        self.serial_manager = SerialConnectionManager(self)
        
        # Create main window
        self.main_window = MainWindow(self)
        self.main_window.show()
        
        # Set up device detection timer
        self.detection_timer = QTimer(self)
        self.detection_timer.timeout.connect(self.device_manager.scan_devices)
        self.detection_timer.start(2000)  # Scan every 2 seconds
        
        logger.info(f"Application started on {platform.system()} {platform.release()}")
    
    def apply_theme(self):
        """Apply the application theme based on settings"""
        # Theme application removed - using default Qt theme only
        pass
    
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Handle keyboard interrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        
        # Show error dialog
        error_msg = QMessageBox()
        error_msg.setIcon(QMessageBox.Icon.Critical)
        error_msg.setWindowTitle("Application Error")
        error_msg.setText("An unexpected error occurred.")
        error_msg.setInformativeText(str(exc_value))
        error_msg.setDetailedText(f"Type: {exc_type.__name__}\nValue: {exc_value}")
        error_msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        error_msg.exec()
    
    def shutdown(self):
        """Clean up resources and prepare for application shutdown"""
        logger.info("Application shutting down")
        
        # Stop device detection timer
        self.detection_timer.stop()
        
        # Close all connections
        self.serial_manager.close_all_connections()
        
        # Save session
        self.session_manager.save_current_session()
        
        # Save configuration
        self.config.save()