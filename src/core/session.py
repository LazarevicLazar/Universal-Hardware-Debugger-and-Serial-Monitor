#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Session management
"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime
import os
import shutil

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages debugging sessions, including saving and loading session state"""
    
    def __init__(self, app):
        """Initialize the session manager"""
        self.app = app
        
        # Define the sessions directory
        self.sessions_dir = Path.home() / '.universal_debugger' / 'sessions'
        self.sessions_dir.mkdir(exist_ok=True)
        
        # Current session information
        self.current_session = {
            "id": int(time.time()),
            "name": f"Session {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "created": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "devices": [],
            "connections": [],
            "ui_state": {},
            "visualizations": []
        }
        
        # Load the last session if auto-load is enabled
        if self.app.config.get("session", "auto_load_last_session", False):
            self.load_last_session()
    
    def save_current_session(self, name=None):
        """Save the current session to a file"""
        try:
            # Update session metadata
            if name:
                self.current_session["name"] = name
            
            self.current_session["last_modified"] = datetime.now().isoformat()
            
            # Update device and connection information
            self._update_session_data()
            
            # Create the session file
            session_file = self.sessions_dir / f"session_{self.current_session['id']}.json"
            
            with open(session_file, 'w') as f:
                json.dump(self.current_session, f, indent=4)
            
            logger.info(f"Session saved to {session_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            return False
    
    def load_session(self, session_id):
        """Load a session from a file"""
        try:
            session_file = self.sessions_dir / f"session_{session_id}.json"
            
            if not session_file.exists():
                logger.error(f"Session file not found: {session_file}")
                return False
            
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Store the current session
            self.current_session = session_data
            
            # Apply the session data to the application
            self._apply_session_data()
            
            logger.info(f"Session loaded from {session_file}")
            return True
        except Exception as e:
            logger.error(f"Error loading session: {e}")
            return False
    
    def load_last_session(self):
        """Load the most recent session"""
        try:
            # Find the most recent session file
            session_files = list(self.sessions_dir.glob("session_*.json"))
            
            if not session_files:
                logger.info("No previous sessions found")
                return False
            
            # Sort by modification time (newest first)
            session_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Extract the session ID from the filename
            session_id = session_files[0].stem.split('_')[1]
            
            return self.load_session(session_id)
        except Exception as e:
            logger.error(f"Error loading last session: {e}")
            return False
    
    def list_sessions(self):
        """List all saved sessions"""
        try:
            sessions = []
            
            for session_file in self.sessions_dir.glob("session_*.json"):
                try:
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)
                    
                    sessions.append({
                        "id": session_data.get("id"),
                        "name": session_data.get("name"),
                        "created": session_data.get("created"),
                        "last_modified": session_data.get("last_modified"),
                        "device_count": len(session_data.get("devices", [])),
                        "file_path": str(session_file)
                    })
                except Exception as e:
                    logger.warning(f"Error reading session file {session_file}: {e}")
            
            # Sort by last modified time (newest first)
            sessions.sort(key=lambda x: x.get("last_modified", ""), reverse=True)
            
            return sessions
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []
    
    def delete_session(self, session_id):
        """Delete a saved session"""
        try:
            session_file = self.sessions_dir / f"session_{session_id}.json"
            
            if not session_file.exists():
                logger.error(f"Session file not found: {session_file}")
                return False
            
            # Delete the file
            session_file.unlink()
            
            logger.info(f"Session deleted: {session_file}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False
    
    def create_new_session(self):
        """Create a new empty session"""
        # Save the current session first
        self.save_current_session()
        
        # Create a new session
        self.current_session = {
            "id": int(time.time()),
            "name": f"Session {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "created": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "devices": [],
            "connections": [],
            "ui_state": {},
            "visualizations": []
        }
        
        logger.info("New session created")
        return True
    
    def _update_session_data(self):
        """Update the session data with current application state"""
        # Get device information
        if hasattr(self.app, 'device_manager'):
            self.current_session["devices"] = self.app.device_manager.get_device_list()
        
        # Get connection information
        if hasattr(self.app, 'serial_manager'):
            self.current_session["connections"] = self.app.serial_manager.get_connection_list()
        
        # Get UI state
        if hasattr(self.app, 'main_window'):
            self.current_session["ui_state"] = self.app.main_window.get_ui_state()
        
        # Get visualization state
        if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'visualization_panel'):
            self.current_session["visualizations"] = self.app.main_window.visualization_panel.get_visualization_state()
    
    def _apply_session_data(self):
        """Apply the loaded session data to the application"""
        # Restore device connections
        if hasattr(self.app, 'device_manager') and "devices" in self.current_session:
            self.app.device_manager.restore_devices(self.current_session["devices"])
        
        # Restore connections
        if hasattr(self.app, 'serial_manager') and "connections" in self.current_session:
            self.app.serial_manager.restore_connections(self.current_session["connections"])
        
        # Restore UI state
        if hasattr(self.app, 'main_window') and "ui_state" in self.current_session:
            self.app.main_window.restore_ui_state(self.current_session["ui_state"])
        
        # Restore visualizations
        if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'visualization_panel') and "visualizations" in self.current_session:
            self.app.main_window.visualization_panel.restore_visualization_state(self.current_session["visualizations"])
    
    def export_session(self, session_id, export_path):
        """Export a session to a file"""
        try:
            session_file = self.sessions_dir / f"session_{session_id}.json"
            
            if not session_file.exists():
                logger.error(f"Session file not found: {session_file}")
                return False
            
            # Copy the session file to the export path
            shutil.copy2(session_file, export_path)
            
            logger.info(f"Session exported to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting session: {e}")
            return False
    
    def import_session(self, import_path):
        """Import a session from a file"""
        try:
            # Validate the import file
            with open(import_path, 'r') as f:
                session_data = json.load(f)
            
            # Ensure the file has the required fields
            required_fields = ["id", "name", "created", "last_modified"]
            for field in required_fields:
                if field not in session_data:
                    logger.error(f"Invalid session file: missing field '{field}'")
                    return False
            
            # Create a new session ID to avoid conflicts
            new_id = int(time.time())
            session_data["id"] = new_id
            
            # Save the imported session
            session_file = self.sessions_dir / f"session_{new_id}.json"
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=4)
            
            logger.info(f"Session imported to {session_file}")
            return new_id
        except Exception as e:
            logger.error(f"Error importing session: {e}")
            return False