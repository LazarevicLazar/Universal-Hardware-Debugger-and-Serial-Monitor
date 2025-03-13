#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Command interface for sending commands to devices
"""

import logging
import json
import time
import threading
import queue
from datetime import datetime, timedelta
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

logger = logging.getLogger(__name__)

class CommandInterface(QObject):
    """Interface for sending commands to devices and managing command history"""
    
    # Signals
    command_sent = pyqtSignal(str, str)  # port, command
    command_scheduled = pyqtSignal(str, str, str)  # port, command, scheduled_time
    command_executed = pyqtSignal(str, str, bool)  # port, command, success
    
    def __init__(self, app):
        """Initialize the command interface"""
        super().__init__()
        
        self.app = app
        
        # Command history
        self.history = []
        self.history_max_size = 100
        
        # Favorite commands
        self.favorites = []
        
        # Command macros
        self.macros = {}
        
        # Scheduled commands
        self.scheduled_commands = []
        self.schedule_timer = QTimer(self)
        self.schedule_timer.timeout.connect(self._check_scheduled_commands)
        self.schedule_timer.start(1000)  # Check every second
        
        # Load saved data
        self._load_data()
    
    def send_command(self, port, command, add_to_history=True):
        """Send a command to a device"""
        try:
            # Get the serial manager
            serial_manager = self.app.serial_manager
            
            # Check if the port is connected
            if not serial_manager.get_connection(port):
                logger.warning(f"Cannot send command: port not connected ({port})")
                self.command_executed.emit(port, command, False)
                return False
            
            # Send the command
            success = serial_manager.send_data(port, command)
            
            # Add to history if successful and requested
            if success and add_to_history:
                self._add_to_history(port, command)
            
            # Emit signal
            self.command_sent.emit(port, command)
            self.command_executed.emit(port, command, success)
            
            return success
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            self.command_executed.emit(port, command, False)
            return False
    
    def broadcast_command(self, command, add_to_history=True):
        """Send a command to all connected devices"""
        try:
            # Get the serial manager
            serial_manager = self.app.serial_manager
            
            # Get all connected ports
            connections = serial_manager.get_connections()
            
            if not connections:
                logger.warning("Cannot broadcast command: no devices connected")
                return False
            
            # Send to all connected ports
            success = True
            for port in connections:
                if not self.send_command(port, command, add_to_history=False):
                    success = False
            
            # Add to history if requested
            if add_to_history:
                self._add_to_history("broadcast", command)
            
            return success
        except Exception as e:
            logger.error(f"Error broadcasting command: {e}")
            return False
    
    def schedule_command(self, port, command, delay_seconds=0, repeat=False, repeat_interval=0):
        """Schedule a command to be sent later"""
        try:
            # Calculate the execution time
            execution_time = datetime.now() + timedelta(seconds=delay_seconds)
            
            # Create the scheduled command
            scheduled_command = {
                "port": port,
                "command": command,
                "execution_time": execution_time,
                "repeat": repeat,
                "repeat_interval": repeat_interval,
                "next_execution": execution_time
            }
            
            # Add to the scheduled commands list
            self.scheduled_commands.append(scheduled_command)
            
            # Emit signal
            self.command_scheduled.emit(port, command, execution_time.strftime("%Y-%m-%d %H:%M:%S"))
            
            logger.info(f"Command scheduled: {command} on {port} at {execution_time}")
            return True
        except Exception as e:
            logger.error(f"Error scheduling command: {e}")
            return False
    
    def cancel_scheduled_command(self, index):
        """Cancel a scheduled command"""
        try:
            if 0 <= index < len(self.scheduled_commands):
                command = self.scheduled_commands.pop(index)
                logger.info(f"Scheduled command canceled: {command['command']} on {command['port']}")
                return True
            else:
                logger.warning(f"Invalid scheduled command index: {index}")
                return False
        except Exception as e:
            logger.error(f"Error canceling scheduled command: {e}")
            return False
    
    def add_to_favorites(self, command, description=""):
        """Add a command to favorites"""
        try:
            # Check if already in favorites
            for favorite in self.favorites:
                if favorite["command"] == command:
                    logger.warning(f"Command already in favorites: {command}")
                    return False
            
            # Add to favorites
            self.favorites.append({
                "command": command,
                "description": description,
                "added": datetime.now().isoformat()
            })
            
            # Save favorites
            self._save_data()
            
            logger.info(f"Command added to favorites: {command}")
            return True
        except Exception as e:
            logger.error(f"Error adding command to favorites: {e}")
            return False
    
    def remove_from_favorites(self, index):
        """Remove a command from favorites"""
        try:
            if 0 <= index < len(self.favorites):
                command = self.favorites.pop(index)
                
                # Save favorites
                self._save_data()
                
                logger.info(f"Command removed from favorites: {command['command']}")
                return True
            else:
                logger.warning(f"Invalid favorite command index: {index}")
                return False
        except Exception as e:
            logger.error(f"Error removing command from favorites: {e}")
            return False
    
    def create_macro(self, name, commands, description=""):
        """Create a command macro"""
        try:
            # Check if name already exists
            if name in self.macros:
                logger.warning(f"Macro already exists: {name}")
                return False
            
            # Create the macro
            self.macros[name] = {
                "name": name,
                "commands": commands,
                "description": description,
                "created": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat()
            }
            
            # Save macros
            self._save_data()
            
            logger.info(f"Macro created: {name} with {len(commands)} commands")
            return True
        except Exception as e:
            logger.error(f"Error creating macro: {e}")
            return False
    
    def update_macro(self, name, commands=None, description=None):
        """Update a command macro"""
        try:
            # Check if macro exists
            if name not in self.macros:
                logger.warning(f"Macro not found: {name}")
                return False
            
            # Update the macro
            if commands is not None:
                self.macros[name]["commands"] = commands
            
            if description is not None:
                self.macros[name]["description"] = description
            
            self.macros[name]["last_modified"] = datetime.now().isoformat()
            
            # Save macros
            self._save_data()
            
            logger.info(f"Macro updated: {name}")
            return True
        except Exception as e:
            logger.error(f"Error updating macro: {e}")
            return False
    
    def delete_macro(self, name):
        """Delete a command macro"""
        try:
            # Check if macro exists
            if name not in self.macros:
                logger.warning(f"Macro not found: {name}")
                return False
            
            # Delete the macro
            del self.macros[name]
            
            # Save macros
            self._save_data()
            
            logger.info(f"Macro deleted: {name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting macro: {e}")
            return False
    
    def execute_macro(self, name, port):
        """Execute a command macro"""
        try:
            # Check if macro exists
            if name not in self.macros:
                logger.warning(f"Macro not found: {name}")
                return False
            
            # Get the commands
            commands = self.macros[name]["commands"]
            
            # Execute each command
            success = True
            for command in commands:
                # Check for delay command
                if command.startswith("DELAY:"):
                    try:
                        delay_seconds = float(command.split(":", 1)[1])
                        time.sleep(delay_seconds)
                    except Exception as e:
                        logger.error(f"Error processing delay command: {e}")
                        success = False
                else:
                    # Send the command
                    if not self.send_command(port, command):
                        success = False
            
            return success
        except Exception as e:
            logger.error(f"Error executing macro: {e}")
            return False
    
    def get_history(self):
        """Get the command history"""
        return self.history
    
    def clear_history(self):
        """Clear the command history"""
        self.history = []
        self._save_data()
        logger.info("Command history cleared")
        return True
    
    def get_favorites(self):
        """Get the favorite commands"""
        return self.favorites
    
    def get_macros(self):
        """Get the command macros"""
        return self.macros
    
    def get_scheduled_commands(self):
        """Get the scheduled commands"""
        return self.scheduled_commands
    
    def _add_to_history(self, port, command):
        """Add a command to the history"""
        # Create history entry
        entry = {
            "port": port,
            "command": command,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to history
        self.history.append(entry)
        
        # Trim history if needed
        if len(self.history) > self.history_max_size:
            self.history = self.history[-self.history_max_size:]
        
        # Save history
        self._save_data()
    
    def _check_scheduled_commands(self):
        """Check for scheduled commands that need to be executed"""
        current_time = datetime.now()
        commands_to_remove = []
        
        for i, command in enumerate(self.scheduled_commands):
            if current_time >= command["next_execution"]:
                # Execute the command
                port = command["port"]
                cmd = command["command"]
                
                if port == "broadcast":
                    self.broadcast_command(cmd)
                else:
                    self.send_command(port, cmd)
                
                # Handle repeating commands
                if command["repeat"]:
                    # Calculate next execution time
                    command["next_execution"] = current_time + timedelta(seconds=command["repeat_interval"])
                else:
                    # Mark for removal
                    commands_to_remove.append(i)
        
        # Remove completed non-repeating commands
        for i in sorted(commands_to_remove, reverse=True):
            self.scheduled_commands.pop(i)
    
    def _load_data(self):
        """Load saved command data"""
        try:
            # Define the data file
            data_dir = Path.home() / '.universal_debugger'
            data_file = data_dir / 'command_data.json'
            
            if data_file.exists():
                with open(data_file, 'r') as f:
                    data = json.load(f)
                
                # Load history
                if "history" in data:
                    self.history = data["history"]
                
                # Load favorites
                if "favorites" in data:
                    self.favorites = data["favorites"]
                
                # Load macros
                if "macros" in data:
                    self.macros = data["macros"]
                
                logger.info(f"Command data loaded from {data_file}")
        except Exception as e:
            logger.error(f"Error loading command data: {e}")
    
    def _save_data(self):
        """Save command data"""
        try:
            # Define the data file
            data_dir = Path.home() / '.universal_debugger'
            data_file = data_dir / 'command_data.json'
            
            # Create the data directory if it doesn't exist
            data_dir.mkdir(exist_ok=True)
            
            # Prepare the data
            data = {
                "history": self.history,
                "favorites": self.favorites,
                "macros": self.macros
            }
            
            # Save the data
            with open(data_file, 'w') as f:
                json.dump(data, f, indent=4)
            
            logger.debug(f"Command data saved to {data_file}")
        except Exception as e:
            logger.error(f"Error saving command data: {e}")