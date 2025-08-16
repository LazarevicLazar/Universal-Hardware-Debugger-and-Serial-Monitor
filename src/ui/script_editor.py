#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Script editor for creating and editing automation scripts
"""

import logging
import time
import re
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
import threading
import queue
import io
import contextlib

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QComboBox, QCheckBox, QLineEdit, QTabWidget,
    QSplitter, QToolBar, QFileDialog, QMessageBox, QMenu,
    QSpinBox, QGroupBox, QFormLayout, QRadioButton, QButtonGroup,
    QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QListWidget, QListWidgetItem, QScrollArea,
    QTreeWidget, QTreeWidgetItem, QPlainTextEdit, QStatusBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QProcess
from PyQt6.QtGui import (
    QAction, QIcon, QColor, QPen, QBrush, QPainter, QPainterPath,
    QTextCursor, QSyntaxHighlighter, QTextCharFormat, QFont,
    QFontMetrics
)

logger = logging.getLogger(__name__)

class ScriptEditor(QWidget):
    """Widget for creating and editing automation scripts"""
    
    def __init__(self, app):
        """Initialize the script editor"""
        super().__init__()
        
        self.app = app
        
        # Script storage
        self.scripts = {}  # name -> {content, type, last_modified}
        self.current_script = None
        
        # Script execution
        self.script_running = False
        self.script_output = ""
        self.script_process = None
        self.script_timeout_timer = None
        self.resource_monitor_timer = None
        
        # Initialize UI components
        self._init_ui()
        
        # Load scripts
        self._load_scripts()
    
    def _init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create a splitter for script list and editor
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left side - Script list
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        # Script type selection
        type_layout = QHBoxLayout()
        left_layout.addLayout(type_layout)
        
        type_layout.addWidget(QLabel("Script Type:"))
        
        self.script_type_combo = QComboBox()
        self.script_type_combo.addItem("Simple Automation", "simple")
        self.script_type_combo.addItem("Python Script", "python")
        type_layout.addWidget(self.script_type_combo)
        
        # Script list
        left_layout.addWidget(QLabel("Scripts:"))
        
        self.script_list = QTreeWidget()
        self.script_list.setHeaderLabels(["Name", "Type"])
        self.script_list.setColumnWidth(0, 200)
        self.script_list.setAlternatingRowColors(True)
        self.script_list.itemSelectionChanged.connect(self._script_selected)
        self.script_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.script_list.customContextMenuRequested.connect(self._show_script_context_menu)
        left_layout.addWidget(self.script_list)
        
        # Button layout
        button_layout = QHBoxLayout()
        left_layout.addLayout(button_layout)
        
        new_script_button = QPushButton("New Script")
        new_script_button.clicked.connect(self._new_script)
        button_layout.addWidget(new_script_button)
        
        delete_script_button = QPushButton("Delete")
        delete_script_button.clicked.connect(self._delete_script)
        button_layout.addWidget(delete_script_button)
        
        # Right side - Editor and output
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        # Editor toolbar
        editor_toolbar = QToolBar()
        right_layout.addWidget(editor_toolbar)
        
        # Save action
        save_action = QAction("Save", self)
        save_action.triggered.connect(self._save_script)
        editor_toolbar.addAction(save_action)
        
        # Run action
        self.run_action = QAction("Run", self)
        self.run_action.triggered.connect(self._run_script)
        editor_toolbar.addAction(self.run_action)
        
        # Stop action
        self.stop_action = QAction("Stop", self)
        self.stop_action.triggered.connect(self._stop_script)
        self.stop_action.setEnabled(False)
        editor_toolbar.addAction(self.stop_action)
        
        editor_toolbar.addSeparator()
        
        # Export action
        export_action = QAction("Export", self)
        export_action.triggered.connect(self._export_script)
        editor_toolbar.addAction(export_action)
        
        # Import action
        import_action = QAction("Import", self)
        import_action.triggered.connect(self._import_script)
        editor_toolbar.addAction(import_action)
        
        # Create a vertical splitter for editor and output
        editor_splitter = QSplitter(Qt.Orientation.Vertical)
        right_layout.addWidget(editor_splitter)
        
        # Script editor
        self.editor = PythonEditor()
        editor_splitter.addWidget(self.editor)
        
        # Output panel
        output_widget = QWidget()
        output_layout = QVBoxLayout()
        output_widget.setLayout(output_layout)
        
        output_layout.addWidget(QLabel("Output:"))
        
        self.output_text = QPlainTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        
        editor_splitter.addWidget(output_widget)
        
        # Set the splitter sizes
        splitter.setSizes([200, 600])
        editor_splitter.setSizes([400, 200])
        
        # Status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _load_scripts(self):
        """Load scripts from the scripts directory"""
        try:
            # Get the scripts directory
            scripts_dir = self.app.config.get("scripting", "script_directory")
            
            if not scripts_dir:
                scripts_dir = str(Path.home() / '.universal_debugger' / 'scripts')
                self.app.config.set("scripting", "script_directory", scripts_dir)
            
            # Create the directory if it doesn't exist
            Path(scripts_dir).mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories for script types
            Path(scripts_dir, "simple").mkdir(exist_ok=True)
            Path(scripts_dir, "python").mkdir(exist_ok=True)
            
            # Load simple scripts
            simple_dir = Path(scripts_dir, "simple")
            for script_file in simple_dir.glob("*.txt"):
                try:
                    with open(script_file, 'r') as f:
                        content = f.read()
                    
                    name = script_file.stem
                    self.scripts[name] = {
                        "content": content,
                        "type": "simple",
                        "last_modified": script_file.stat().st_mtime
                    }
                except Exception as e:
                    logger.error(f"Error loading simple script {script_file}: {e}")
            
            # Load Python scripts
            python_dir = Path(scripts_dir, "python")
            for script_file in python_dir.glob("*.py"):
                try:
                    with open(script_file, 'r') as f:
                        content = f.read()
                    
                    name = script_file.stem
                    self.scripts[name] = {
                        "content": content,
                        "type": "python",
                        "last_modified": script_file.stat().st_mtime
                    }
                except Exception as e:
                    logger.error(f"Error loading Python script {script_file}: {e}")
            
            # Update the script list
            self._update_script_list()
            
            logger.info(f"Loaded {len(self.scripts)} scripts")
        except Exception as e:
            logger.error(f"Error loading scripts: {e}")
            QMessageBox.critical(self, "Error", f"Error loading scripts: {e}")
    
    def _update_script_list(self):
        """Update the script list"""
        try:
            # Clear the list
            self.script_list.clear()
            
            # Create category items
            simple_category = QTreeWidgetItem(self.script_list, ["Simple Automation"])
            python_category = QTreeWidgetItem(self.script_list, ["Python Scripts"])
            
            # Add scripts to the appropriate category
            for name, script in self.scripts.items():
                if script["type"] == "simple":
                    item = QTreeWidgetItem(simple_category, [name, "Simple"])
                    item.setData(0, Qt.ItemDataRole.UserRole, name)
                else:
                    item = QTreeWidgetItem(python_category, [name, "Python"])
                    item.setData(0, Qt.ItemDataRole.UserRole, name)
            
            # Expand the categories
            simple_category.setExpanded(True)
            python_category.setExpanded(True)
        except Exception as e:
            logger.error(f"Error updating script list: {e}")
    
    def _script_selected(self):
        """Handle script selection"""
        try:
            # Get the selected item
            selected = self.script_list.selectedItems()
            
            if not selected or not selected[0].parent():
                # No selection or category selected
                return
            
            # Get the script name
            name = selected[0].data(0, Qt.ItemDataRole.UserRole)
            
            if name in self.scripts:
                # Save the current script if there is one
                if self.current_script:
                    self._save_current_script()
                
                # Load the selected script
                script = self.scripts[name]
                self.current_script = name
                
                # Set the editor content
                self.editor.setPlainText(script["content"])
                
                # Set the script type
                index = self.script_type_combo.findData(script["type"])
                if index >= 0:
                    self.script_type_combo.setCurrentIndex(index)
                
                # Update the status bar
                last_modified = datetime.fromtimestamp(script["last_modified"]).strftime("%Y-%m-%d %H:%M:%S")
                self.status_bar.showMessage(f"Script: {name} | Type: {script['type']} | Last Modified: {last_modified}")
        except Exception as e:
            logger.error(f"Error selecting script: {e}")
    
    def _new_script(self):
        """Create a new script"""
        try:
            # Show the new script dialog
            dialog = NewScriptDialog(self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get the script name and type
                name = dialog.get_name()
                script_type = dialog.get_type()
                
                # Check if the name already exists
                if name in self.scripts:
                    QMessageBox.warning(self, "New Script", f"A script with the name '{name}' already exists.")
                    return
                
                # Create the script
                self.scripts[name] = {
                    "content": self._get_script_template(script_type),
                    "type": script_type,
                    "last_modified": time.time()
                }
                
                # Save the script
                self._save_script_to_file(name)
                
                # Update the script list
                self._update_script_list()
                
                # Select the new script
                self._select_script(name)
                
                logger.info(f"Created new script: {name} ({script_type})")
        except Exception as e:
            logger.error(f"Error creating new script: {e}")
            QMessageBox.critical(self, "Error", f"Error creating new script: {e}")
    
    def _get_script_template(self, script_type):
        """Get a template for a new script"""
        if script_type == "simple":
            return "# Simple Automation Script\n# Each line is a command or a DELAY:seconds directive\n\n# Example:\n# AT+GMR\n# DELAY:1\n# AT+CWLAP\n"
        else:
            return """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
Python Script for Universal Hardware Debugger
\"\"\"

import time
import re
import json

# Access to the application API
# app - The main application instance
# serial_manager - The serial connection manager
# device_manager - The device manager
# command_interface - The command interface

def main():
    \"\"\"Main entry point for the script\"\"\"
    print("Script started")
    
    # Example: Get connected devices
    devices = device_manager.get_connected_devices()
    print(f"Connected devices: {len(devices)}")
    
    for device in devices:
        print(f"Device: {device['name']} on {device['port']}")
        
        # Example: Send a command
        command_interface.send_command(device['port'], "AT+GMR")
        
        # Wait for response
        time.sleep(1)
    
    print("Script completed")

if __name__ == "__main__":
    main()
"""
    
    def _delete_script(self):
        """Delete the selected script"""
        try:
            # Get the selected item
            selected = self.script_list.selectedItems()
            
            if not selected or not selected[0].parent():
                # No selection or category selected
                return
            
            # Get the script name
            name = selected[0].data(0, Qt.ItemDataRole.UserRole)
            
            # Confirm deletion
            reply = QMessageBox.question(
                self, "Delete Script",
                f"Are you sure you want to delete the script '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Delete the script file
                self._delete_script_file(name)
                
                # Remove from the scripts dictionary
                if name in self.scripts:
                    del self.scripts[name]
                
                # Clear the editor if this was the current script
                if self.current_script == name:
                    self.current_script = None
                    self.editor.clear()
                    self.status_bar.showMessage("Ready")
                
                # Update the script list
                self._update_script_list()
                
                logger.info(f"Deleted script: {name}")
        except Exception as e:
            logger.error(f"Error deleting script: {e}")
            QMessageBox.critical(self, "Error", f"Error deleting script: {e}")
    
    def _save_script(self):
        """Save the current script"""
        try:
            if not self.current_script:
                return
            
            self._save_current_script()
            
            self.status_bar.showMessage(f"Script '{self.current_script}' saved", 3000)
            logger.info(f"Saved script: {self.current_script}")
        except Exception as e:
            logger.error(f"Error saving script: {e}")
            QMessageBox.critical(self, "Error", f"Error saving script: {e}")
    
    def _save_current_script(self):
        """Save the current script to the scripts dictionary"""
        if not self.current_script:
            return
        
        # Get the script content
        content = self.editor.toPlainText()
        
        # Get the script type
        script_type = self.script_type_combo.currentData()
        
        # Update the script
        self.scripts[self.current_script] = {
            "content": content,
            "type": script_type,
            "last_modified": time.time()
        }
        
        # Save to file
        self._save_script_to_file(self.current_script)
    
    def _save_script_to_file(self, name):
        """Save a script to a file"""
        try:
            script = self.scripts[name]
            
            # Get the scripts directory
            scripts_dir = self.app.config.get("scripting", "script_directory")
            
            # Determine the file path based on the script type
            if script["type"] == "simple":
                file_path = Path(scripts_dir, "simple", f"{name}.txt")
            else:
                file_path = Path(scripts_dir, "python", f"{name}.py")
            
            # Save the script
            with open(file_path, 'w') as f:
                f.write(script["content"])
            
            # Update the last modified time
            script["last_modified"] = file_path.stat().st_mtime
        except Exception as e:
            logger.error(f"Error saving script to file: {e}")
            raise
    
    def _delete_script_file(self, name):
        """Delete a script file"""
        try:
            script = self.scripts.get(name)
            
            if not script:
                return
            
            # Get the scripts directory
            scripts_dir = self.app.config.get("scripting", "script_directory")
            
            # Determine the file path based on the script type
            if script["type"] == "simple":
                file_path = Path(scripts_dir, "simple", f"{name}.txt")
            else:
                file_path = Path(scripts_dir, "python", f"{name}.py")
            
            # Delete the file if it exists
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.error(f"Error deleting script file: {e}")
            raise
    
    def _run_script(self):
        """Run the current script with improved safety"""
        try:
            if not self.current_script:
                QMessageBox.warning(self, "Run Script", "No script selected.")
                return
            
            # Save the script first
            self._save_current_script()
            
            # Get the script
            script = self.scripts[self.current_script]
            
            # Clear the output
            self.output_text.clear()
            self.script_output = ""
            
            # Update UI
            self.run_action.setEnabled(False)
            self.stop_action.setEnabled(True)
            self.script_running = True
            self.status_bar.showMessage(f"Running script: {self.current_script}")
            
            # Get script execution limits from config
            max_execution_time = self.app.config.get("scripting", "max_execution_time", 60)  # seconds
            max_memory_usage = self.app.config.get("scripting", "max_memory_usage", 104857600)  # 100 MB
            
            # Set up execution timeout timer
            self.script_timeout_timer = QTimer(self)
            self.script_timeout_timer.timeout.connect(self._script_timeout)
            self.script_timeout_timer.setSingleShot(True)
            self.script_timeout_timer.start(max_execution_time * 1000)  # Convert to milliseconds
            
            # Run the script in a separate thread
            if script["type"] == "simple":
                threading.Thread(target=self._run_simple_script, daemon=True).start()
            else:
                threading.Thread(target=self._run_python_script, daemon=True).start()
                
            # Start monitoring resource usage
            self.resource_monitor_timer = QTimer(self)
            self.resource_monitor_timer.timeout.connect(self._monitor_script_resources)
            self.resource_monitor_timer.start(1000)  # Check every second
            
        except Exception as e:
            logger.error(f"Error running script: {e}")
            QMessageBox.critical(self, "Error", f"Error running script: {e}")
            self._script_finished()
    
    def _script_timeout(self):
        """Handle script execution timeout"""
        if self.script_running:
            logger.warning(f"Script execution timeout: {self.current_script}")
            self._append_output("\n\nERROR: Script execution timed out and was terminated.")
            self._stop_script(force=True)
    
    def _monitor_script_resources(self):
        """Monitor script resource usage"""
        if not self.script_running or not hasattr(self, 'script_process') or not self.script_process:
            return
        
        try:
            # Check if process is still running
            if self.script_process.poll() is not None:
                self.resource_monitor_timer.stop()
                return
                
            # Get process info
            process = psutil.Process(self.script_process.pid)
            
            # Check memory usage
            memory_info = process.memory_info()
            memory_usage = memory_info.rss
            max_memory = self.app.config.get("scripting", "max_memory_usage", 104857600)  # 100 MB
            
            if memory_usage > max_memory:
                logger.warning(f"Script exceeded memory limit: {memory_usage} bytes > {max_memory} bytes")
                self._append_output(f"\n\nERROR: Script exceeded memory limit ({memory_usage/1048576:.1f} MB > {max_memory/1048576:.1f} MB) and was terminated.")
                self._stop_script(force=True)
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Process already terminated
            self.resource_monitor_timer.stop()
        except Exception as e:
            logger.error(f"Error monitoring script resources: {e}")
    
    def _run_simple_script(self):
        """Run a simple automation script"""
        try:
            script = self.scripts[self.current_script]
            lines = script["content"].splitlines()
            
            self._append_output("Starting simple automation script...\n")
            
            for line in lines:
                # Check if the script has been stopped
                if not self.script_running:
                    self._append_output("\nScript execution stopped.")
                    break
                
                # Skip empty lines and comments
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                # Check for delay directive
                if line.startswith("DELAY:"):
                    try:
                        delay = float(line.split(":", 1)[1])
                        self._append_output(f"Delaying for {delay} seconds...")
                        time.sleep(delay)
                        continue
                    except Exception as e:
                        self._append_output(f"Error processing delay: {e}")
                        continue
                
                # Send the command to all connected devices
                self._append_output(f"Sending: {line}")
                
                if hasattr(self.app, 'command_interface'):
                    success = self.app.command_interface.broadcast_command(line)
                    if success:
                        self._append_output("Command sent successfully.")
                    else:
                        self._append_output("Failed to send command.")
                else:
                    self._append_output("Command interface not available.")
                
                # Small delay between commands
                time.sleep(0.1)
            
            self._append_output("\nScript execution completed.")
        except Exception as e:
            logger.error(f"Error running simple script: {e}")
            self._append_output(f"\nError: {e}")
        finally:
            # Update UI
            self._script_finished()
    
    def _run_python_script(self):
        """Run a Python script in a separate process with safety measures"""
        try:
            script = self.scripts[self.current_script]
            
            self._append_output("Starting Python script in isolated environment...\n")
            
            # Create a temporary directory for script execution
            temp_dir = tempfile.mkdtemp(prefix="script_")
            
            # Create a unique ID for this script execution
            execution_id = str(uuid.uuid4())
            
            # Create the script file
            script_path = os.path.join(temp_dir, f"{self.current_script}.py")
            
            # Create a wrapper script that provides a restricted API
            wrapper_script = self._create_script_wrapper(script["content"], execution_id)
            wrapper_path = os.path.join(temp_dir, f"wrapper_{execution_id}.py")
            
            # Write the scripts to disk
            with open(script_path, 'w') as f:
                f.write(script["content"])
                
            with open(wrapper_path, 'w') as f:
                f.write(wrapper_script)
            
            # Get Python path from config or use system Python
            python_path = self.app.config.get("scripting", "python_path", "")
            if not python_path:
                python_path = sys.executable
                
            # Create a pipe for communication
            self.script_output_queue = multiprocessing.Queue()
            
            # Start the process
            self._append_output(f"Executing script with Python: {python_path}\n")
            
            # Create environment with restricted modules
            env = os.environ.copy()
            allowed_modules = self.app.config.get("scripting", "allowed_modules",
                                                ["time", "math", "random", "datetime", "json", "re"])
            env["PYTHONPATH"] = temp_dir
            
            # Start the process
            self.script_process = subprocess.Popen(
                [python_path, wrapper_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=temp_dir
            )
            
            # Start threads to read output
            threading.Thread(target=self._read_process_output,
                            args=(self.script_process.stdout, False),
                            daemon=True).start()
            threading.Thread(target=self._read_process_output,
                            args=(self.script_process.stderr, True),
                            daemon=True).start()
            
            # Wait for the process to complete
            self.script_process.wait()
            
            # Check return code
            if self.script_process.returncode != 0:
                self._append_output(f"\nScript exited with error code: {self.script_process.returncode}")
            else:
                self._append_output("\nScript execution completed successfully.")
                
            # Clean up
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Error cleaning up temporary directory: {e}")
                
        except Exception as e:
            logger.error(f"Error running Python script: {e}")
            self._append_output(f"\nError: {e}")
            self._append_output(f"\nTraceback:\n{traceback.format_exc()}")
        finally:
            # Update UI
            self._script_finished()
    
    def _create_script_wrapper(self, script_content, execution_id):
        """Create a wrapper script that provides a restricted API"""
        # Get allowed modules from config
        allowed_modules = self.app.config.get("scripting", "allowed_modules",
                                             ["time", "math", "random", "datetime", "json", "re"])
        
        # Create the wrapper script
        wrapper = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
Secure wrapper for user script execution
\"\"\"

import sys
import os
import importlib
import time
import json
import traceback

# Set resource limits
try:
    import resource
    # Set CPU time limit (seconds)
    resource.setrlimit(resource.RLIMIT_CPU, ({self.app.config.get("scripting", "max_execution_time", 60)}, {self.app.config.get("scripting", "max_execution_time", 60)}))
    # Set memory limit (bytes)
    resource.setrlimit(resource.RLIMIT_AS, ({self.app.config.get("scripting", "max_memory_usage", 104857600)}, {self.app.config.get("scripting", "max_memory_usage", 104857600)}))
except ImportError:
    print("Warning: resource module not available, cannot set resource limits")

# Set up restricted imports
allowed_modules = {allowed_modules}
original_import = __builtins__.__import__

def restricted_import(name, *args, **kwargs):
    if name in allowed_modules:
        return original_import(name, *args, **kwargs)
    else:
        raise ImportError(f"Import of module {{name}} is not allowed")

__builtins__.__import__ = restricted_import

# Set up the API
class RestrictedAPI:
    def __init__(self):
        self.start_time = time.time()
        self.max_execution_time = {self.app.config.get("scripting", "max_execution_time", 60)}
    
    def check_timeout(self):
        if time.time() - self.start_time > self.max_execution_time:
            raise TimeoutError(f"Script execution exceeded maximum time of {{self.max_execution_time}} seconds")
    
    def send_command(self, port, command):
        print(f"[COMMAND] Sending command to {{port}}: {{command}}")
        # In a real implementation, this would communicate with the parent process
        return True
    
    def get_device_list(self):
        print("[API] Getting device list")
        # In a real implementation, this would communicate with the parent process
        return []
    
    def get_connection_info(self, port):
        print(f"[API] Getting connection info for {{port}}")
        # In a real implementation, this would communicate with the parent process
        return {{"port": port, "connected": False}}

# Create the API
api = RestrictedAPI()

# Run the user script with periodic timeout checks
try:
    # Import the user script
    from {self.current_script} import *
    
    # Check if there's a main function and call it
    if 'main' in globals() and callable(globals()['main']):
        main()
    
except Exception as e:
    print(f"Error: {{type(e).__name__}}: {{str(e)}}")
    print(traceback.format_exc())
    sys.exit(1)

sys.exit(0)
"""
        return wrapper
    
    def _read_process_output(self, pipe, is_error):
        """Read output from the script process"""
        prefix = "ERROR: " if is_error else ""
        
        for line in iter(pipe.readline, ''):
            if not line:
                break
                
            if line.startswith('[COMMAND]'):
                # Handle command from script
                self._handle_script_command(line)
            elif line.startswith('[API]'):
                # Handle API call from script
                pass  # Just log it for now
            else:
                # Regular output
                self._append_output(f"{prefix}{line}")
    
    def _script_print(self, *args, **kwargs):
        """Custom print function for scripts"""
        # Convert args to string
        output = " ".join(str(arg) for arg in args)
        
        # Add newline if not present
        if not output.endswith("\n"):
            output += "\n"
        
        # Append to output
        self._append_output(output)
    
    def _append_output(self, text):
        """Append text to the output panel"""
        self.script_output += text
        
        # Update the output text in the UI thread
        self.output_text.setPlainText(self.script_output)
        
        # Scroll to the bottom
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_text.setTextCursor(cursor)
    
    def _script_finished(self):
        """Handle script execution finished"""
        self.script_running = False
        self.run_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.status_bar.showMessage(f"Script '{self.current_script}' execution finished")
    
    def _stop_script(self, force=False):
        """Stop the current script execution"""
        self.script_running = False
        self.status_bar.showMessage(f"Stopping script: {self.current_script}")
        
        # Stop the timeout timer if it's running
        if hasattr(self, 'script_timeout_timer') and self.script_timeout_timer.isActive():
            self.script_timeout_timer.stop()
            
        # Stop the resource monitor if it's running
        if hasattr(self, 'resource_monitor_timer') and self.resource_monitor_timer.isActive():
            self.resource_monitor_timer.stop()
        
        # Terminate the process if it's running
        if hasattr(self, 'script_process') and self.script_process:
            try:
                if force:
                    # Force kill the process
                    self.script_process.kill()
                else:
                    # Try to terminate gracefully first
                    self.script_process.terminate()
                    
                    # Wait a bit for it to terminate
                    for _ in range(5):  # Wait up to 0.5 seconds
                        if self.script_process.poll() is not None:
                            break
                        time.sleep(0.1)
                    
                    # If still running, force kill
                    if self.script_process.poll() is None:
                        self.script_process.kill()
                        
                self._append_output("\nScript execution stopped.")
            except Exception as e:
                logger.error(f"Error stopping script process: {e}")
    
    def _handle_script_command(self, command_line):
        """Handle a command from the script"""
        try:
            # Parse the command
            command_text = command_line.strip()[9:]  # Remove '[COMMAND] ' prefix
            
            if command_text.startswith("Sending command to "):
                # Extract port and command
                parts = command_text.split(": ", 1)
                if len(parts) == 2:
                    port_part = parts[0].replace("Sending command to ", "")
                    command = parts[1]
                    
                    # Execute the command if we have a command interface
                    if hasattr(self.app, 'command_interface'):
                        if port_part == "all":
                            success = self.app.command_interface.broadcast_command(command)
                        else:
                            success = self.app.command_interface.send_command(port_part, command)
                        
                        self._append_output(f"Command sent: {command} to {port_part}, success: {success}")
                    else:
                        self._append_output("Command interface not available.")
        except Exception as e:
            logger.error(f"Error handling script command: {e}")
    
    def _export_script(self):
        """Export the current script to a file"""
        try:
            if not self.current_script:
                QMessageBox.warning(self, "Export Script", "No script selected.")
                return
            
            # Save the script first
            self._save_current_script()
            
            # Get the script
            script = self.scripts[self.current_script]
            
            # Determine the default file extension
            if script["type"] == "simple":
                file_filter = "Text Files (*.txt)"
                default_ext = ".txt"
            else:
                file_filter = "Python Files (*.py)"
                default_ext = ".py"
            
            # Show a file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Script", f"{self.current_script}{default_ext}", file_filter
            )
            
            if not file_path:
                return
            
            # Export the script
            with open(file_path, 'w') as f:
                f.write(script["content"])
            
            self.status_bar.showMessage(f"Script exported to {file_path}", 3000)
            logger.info(f"Exported script: {self.current_script} to {file_path}")
        except Exception as e:
            logger.error(f"Error exporting script: {e}")
            QMessageBox.critical(self, "Error", f"Error exporting script: {e}")
    
    def _import_script(self):
        """Import a script from a file"""
        try:
            # Show a file dialog
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Import Script", "", "Script Files (*.txt *.py)"
            )
            
            if not file_path:
                return
            
            # Determine the script type based on the file extension
            if file_path.endswith(".py"):
                script_type = "python"
            else:
                script_type = "simple"
            
            # Get the script name from the file name
            name = Path(file_path).stem
            
            # Check if the name already exists
            if name in self.scripts:
                reply = QMessageBox.question(
                    self, "Import Script",
                    f"A script with the name '{name}' already exists. Overwrite?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # Read the script content
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Create or update the script
            self.scripts[name] = {
                "content": content,
                "type": script_type,
                "last_modified": time.time()
            }
            
            # Save the script
            self._save_script_to_file(name)
            
            # Update the script list
            self._update_script_list()
            
            # Select the imported script
            self._select_script(name)
            
            self.status_bar.showMessage(f"Script imported: {name}", 3000)
            logger.info(f"Imported script: {name} from {file_path}")
        except Exception as e:
            logger.error(f"Error importing script: {e}")
            QMessageBox.critical(self, "Error", f"Error importing script: {e}")
    
    def _select_script(self, name):
        """Select a script in the list"""
        try:
            # Find the script item
            for i in range(self.script_list.topLevelItemCount()):
                category = self.script_list.topLevelItem(i)
                
                for j in range(category.childCount()):
                    item = category.child(j)
                    
                    if item.data(0, Qt.ItemDataRole.UserRole) == name:
                        # Select the item
                        self.script_list.setCurrentItem(item)
                        return
        except Exception as e:
            logger.error(f"Error selecting script: {e}")
    
    def _show_script_context_menu(self, position):
        """Show the context menu for the script list"""
        try:
            # Get the selected item
            item = self.script_list.itemAt(position)
            
            if not item or not item.parent():
                # No selection or category selected
                return
            
            # Create the menu
            menu = QMenu()
            
            # Run action
            run_action = QAction("Run", self)
            run_action.triggered.connect(self._run_script)
            menu.addAction(run_action)
            
            # Export action
            export_action = QAction("Export", self)
            export_action.triggered.connect(self._export_script)
            menu.addAction(export_action)
            
            menu.addSeparator()
            
            # Rename action
            rename_action = QAction("Rename", self)
            rename_action.triggered.connect(lambda: self._rename_script(item))
            menu.addAction(rename_action)
            
            # Delete action
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(self._delete_script)
            menu.addAction(delete_action)
            
            # Show the menu
            menu.exec(self.script_list.viewport().mapToGlobal(position))
        except Exception as e:
            logger.error(f"Error showing script context menu: {e}")
    
    def _rename_script(self, item):
        """Rename a script"""
        try:
            # Get the script name
            old_name = item.data(0, Qt.ItemDataRole.UserRole)
            
            # Show the rename dialog
            dialog = RenameScriptDialog(self, old_name)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get the new name
                new_name = dialog.get_name()
                
                # Check if the new name already exists
                if new_name in self.scripts and new_name != old_name:
                    QMessageBox.warning(self, "Rename Script", f"A script with the name '{new_name}' already exists.")
                    return
                
                # Get the script
                script = self.scripts[old_name]
                
                # Delete the old script file
                self._delete_script_file(old_name)
                
                # Update the scripts dictionary
                self.scripts[new_name] = script
                del self.scripts[old_name]
                
                # Update the current script if needed
                if self.current_script == old_name:
                    self.current_script = new_name
                
                # Save the script with the new name
                self._save_script_to_file(new_name)
                
                # Update the script list
                self._update_script_list()
                
                # Select the renamed script
                self._select_script(new_name)
                
                logger.info(f"Renamed script: {old_name} to {new_name}")
        except Exception as e:
            logger.error(f"Error renaming script: {e}")
            QMessageBox.critical(self, "Error", f"Error renaming script: {e}")


class NewScriptDialog(QDialog):
    """Dialog for creating a new script"""
    
    def __init__(self, parent):
        """Initialize the dialog"""
        super().__init__(parent)
        
        # Set dialog properties
        self.setWindowTitle("New Script")
        self.setMinimumWidth(300)
        
        # Initialize UI components
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Form layout
        form_layout = QFormLayout()
        layout.addLayout(form_layout)
        
        # Script name
        self.name_input = QLineEdit()
        form_layout.addRow("Name:", self.name_input)
        
        # Script type
        self.type_combo = QComboBox()
        self.type_combo.addItem("Simple Automation", "simple")
        self.type_combo.addItem("Python Script", "python")
        form_layout.addRow("Type:", self.type_combo)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def accept(self):
        """Handle dialog acceptance"""
        # Validate the script name
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a name for the script.")
            return
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            QMessageBox.warning(self, "Validation Error", "Script name can only contain letters, numbers, underscores, and hyphens.")
            return
        
        # All validation passed
        super().accept()
    
    def get_name(self):
        """Get the script name"""
        return self.name_input.text().strip()
    
    def get_type(self):
        """Get the script type"""
        return self.type_combo.currentData()


class RenameScriptDialog(QDialog):
    """Dialog for renaming a script"""
    
    def __init__(self, parent, old_name):
        """Initialize the dialog"""
        super().__init__(parent)
        
        self.old_name = old_name
        
        # Set dialog properties
        self.setWindowTitle("Rename Script")
        self.setMinimumWidth(300)
        
        # Initialize UI components
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Form layout
        form_layout = QFormLayout()
        layout.addLayout(form_layout)
        
        # Old name
        old_name_label = QLabel(self.old_name)
        form_layout.addRow("Old Name:", old_name_label)
        
        # New name
        self.name_input = QLineEdit(self.old_name)
        form_layout.addRow("New Name:", self.name_input)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def accept(self):
        """Handle dialog acceptance"""
        # Validate the script name
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a name for the script.")
            return
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            QMessageBox.warning(self, "Validation Error", "Script name can only contain letters, numbers, underscores, and hyphens.")
            return
        
        # All validation passed
        super().accept()
    
    def get_name(self):
        """Get the script name"""
        return self.name_input.text().strip()


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Python code"""
    
    def __init__(self, parent=None):
        """Initialize the syntax highlighter"""
        super().__init__(parent)
        
        self.highlighting_rules = []
        
        # Keyword format
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def",
            "del", "elif", "else", "except", "exec", "finally", "for",
            "from", "global", "if", "import", "in", "is", "lambda",
            "not", "or", "pass", "print", "raise", "return", "try",
            "while", "with", "yield"
        ]
        
        for word in keywords:
            pattern = r'\b' + word + r'\b'
            self.highlighting_rules.append((re.compile(pattern), keyword_format))
        
        # Function format
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#DCDCAA"))
        function_format.setFontWeight(QFont.Weight.Bold)
        
        self.highlighting_rules.append((re.compile(r'\b[A-Za-z0-9_]+(?=\()'), function_format))
        
        # String format
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))
        
        self.highlighting_rules.append((re.compile(r'".*?"'), string_format))
        self.highlighting_rules.append((re.compile(r"'.*?'"), string_format))
        
        # Comment format
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        
        self.highlighting_rules.append((re.compile(r'#.*$'), comment_format))
        
        # Number format
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))
        
        self.highlighting_rules.append((re.compile(r'\b[0-9]+\b'), number_format))
    
    def highlightBlock(self, text):
        """Highlight a block of text"""
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, format)


class PythonEditor(QPlainTextEdit):
    """Custom text editor with Python syntax highlighting"""
    
    def __init__(self, parent=None):
        """Initialize the editor"""
        super().__init__(parent)
        
        # Set font
        font = QFont("Courier New", 10)
        self.setFont(font)
        
        # Set tab width
        metrics = QFontMetrics(font)
        self.setTabStopDistance(4 * metrics.horizontalAdvance(' '))
        
        # Set syntax highlighter
        self.highlighter = PythonSyntaxHighlighter(self.document())