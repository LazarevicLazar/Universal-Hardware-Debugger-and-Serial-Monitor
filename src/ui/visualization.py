#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Visualization panel for displaying data visualizations
"""

import logging
import time
import re
import json
import csv
from datetime import datetime
from pathlib import Path
import os
import math
import random

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QCheckBox, QLineEdit, QTabWidget, QSplitter,
    QToolBar, QFileDialog, QMessageBox, QMenu, QSpinBox,
    QGroupBox, QFormLayout, QRadioButton, QButtonGroup,
    QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QListWidget, QListWidgetItem, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QRectF
from PyQt6.QtGui import QAction, QIcon, QColor, QPen, QBrush, QPainter, QPainterPath

import pyqtgraph as pg
import numpy as np

logger = logging.getLogger(__name__)

class VisualizationPanel(QWidget):
    """Panel for displaying data visualizations"""
    
    def __init__(self, app):
        """Initialize the visualization panel"""
        super().__init__()
        
        self.app = app
        
        # Data storage
        self.data_series = {}  # name -> {data, config}
        
        # Chart configuration
        self.max_data_points = 1000
        self.update_interval = 100  # ms
        
        # Initialize UI components
        self._init_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_charts)
        self.update_timer.start(self.update_interval)
    
    def _init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Toolbar
        toolbar = QToolBar()
        layout.addWidget(toolbar)
        
        # Add visualization button
        add_viz_action = QAction("Add Visualization", self)
        add_viz_action.triggered.connect(self._add_visualization)
        toolbar.addAction(add_viz_action)
        
        # Export data button
        export_action = QAction("Export Data", self)
        export_action.triggered.connect(self._export_data)
        toolbar.addAction(export_action)
        
        toolbar.addSeparator()
        
        # Update interval
        toolbar.addWidget(QLabel("Update Interval:"))
        
        self.update_interval_spin = QSpinBox()
        self.update_interval_spin.setRange(50, 5000)
        self.update_interval_spin.setValue(self.update_interval)
        self.update_interval_spin.setSuffix(" ms")
        self.update_interval_spin.valueChanged.connect(self._set_update_interval)
        toolbar.addWidget(self.update_interval_spin)
        
        toolbar.addSeparator()
        
        # Max data points
        toolbar.addWidget(QLabel("Max Data Points:"))
        
        self.max_points_spin = QSpinBox()
        self.max_points_spin.setRange(100, 100000)
        self.max_points_spin.setValue(self.max_data_points)
        self.max_points_spin.valueChanged.connect(self._set_max_data_points)
        toolbar.addWidget(self.max_points_spin)
        
        # Tab widget for visualizations
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_visualization)
        layout.addWidget(self.tab_widget)
        
        # Add a welcome tab
        self._add_welcome_tab()
    
    def _connect_signals(self):
        """Connect signals from the serial manager"""
        # Connect to the serial manager's signals
        if hasattr(self.app, 'serial_manager'):
            for port, connection in self.app.serial_manager.get_connections().items():
                connection.data_received.connect(self._process_data)
    
    def _add_welcome_tab(self):
        """Add a welcome tab with instructions"""
        welcome_tab = QWidget()
        welcome_layout = QVBoxLayout()
        welcome_tab.setLayout(welcome_layout)
        
        welcome_label = QLabel(
            "<h1>Welcome to the Visualization Panel</h1>"
            "<p>This panel allows you to create visualizations of data from your devices.</p>"
            "<p>To get started, click the 'Add Visualization' button in the toolbar.</p>"
            "<p>You can create different types of visualizations:</p>"
            "<ul>"
            "<li><b>Line Chart</b>: For time-series data</li>"
            "<li><b>Bar Chart</b>: For comparing values</li>"
            "<li><b>Gauge</b>: For displaying a single value</li>"
            "</ul>"
            "<p>Data can be parsed from the serial output using regular expressions.</p>"
        )
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setWordWrap(True)
        welcome_layout.addWidget(welcome_label)
        
        # Add a button to create a new visualization
        add_button = QPushButton("Add Visualization")
        add_button.clicked.connect(self._add_visualization)
        welcome_layout.addWidget(add_button)
        
        # Add spacer
        welcome_layout.addStretch()
        
        self.tab_widget.addTab(welcome_tab, "Welcome")
    
    def _add_visualization(self):
        """Add a new visualization"""
        try:
            # Show the add visualization dialog
            dialog = AddVisualizationDialog(self, self.app)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get the visualization configuration
                config = dialog.get_config()
                
                # Create the visualization
                self._create_visualization(config)
        except Exception as e:
            logger.error(f"Error adding visualization: {e}")
            QMessageBox.critical(self, "Error", f"Error adding visualization: {e}")
    
    def _create_visualization(self, config):
        """Create a new visualization based on the configuration"""
        try:
            # Create a unique name for the visualization
            name = config["name"]
            
            # Check if the name already exists
            if name in self.data_series:
                # Add a number to make it unique
                i = 1
                while f"{name} ({i})" in self.data_series:
                    i += 1
                name = f"{name} ({i})"
                config["name"] = name
            
            # Create the data series
            self.data_series[name] = {
                "data": [],
                "config": config,
                "last_update": time.time()
            }
            
            # Create the visualization tab
            tab = QWidget()
            tab_layout = QVBoxLayout()
            tab.setLayout(tab_layout)
            
            # Create the chart based on the type
            if config["type"] == "line":
                chart = self._create_line_chart(name, config)
            elif config["type"] == "bar":
                chart = self._create_bar_chart(name, config)
            elif config["type"] == "gauge":
                chart = self._create_gauge(name, config)
            else:
                raise ValueError(f"Unknown chart type: {config['type']}")
            
            # Add the chart to the tab
            tab_layout.addWidget(chart)
            
            # Add the tab
            self.tab_widget.addTab(tab, name)
            self.tab_widget.setCurrentWidget(tab)
            
            logger.info(f"Created visualization: {name}")
        except Exception as e:
            logger.error(f"Error creating visualization: {e}")
            QMessageBox.critical(self, "Error", f"Error creating visualization: {e}")
    
    def _create_line_chart(self, name, config):
        """Create a line chart"""
        # Create a plot widget
        plot_widget = pg.PlotWidget()
        
        # Set the title and axis labels
        plot_widget.setTitle(config["name"])
        plot_widget.setLabel("left", config["y_label"])
        plot_widget.setLabel("bottom", config["x_label"])
        
        # Create the plot item
        plot = plot_widget.getPlotItem()
        
        # Add a grid
        plot.showGrid(x=True, y=True)
        
        # Create the line
        line = plot.plot(pen=pg.mkPen(color=config["color"], width=2))
        
        # Store the line in the data series
        self.data_series[name]["line"] = line
        
        return plot_widget
    
    def _create_bar_chart(self, name, config):
        """Create a bar chart"""
        # Create a plot widget
        plot_widget = pg.PlotWidget()
        
        # Set the title and axis labels
        plot_widget.setTitle(config["name"])
        plot_widget.setLabel("left", config["y_label"])
        plot_widget.setLabel("bottom", config["x_label"])
        
        # Create the plot item
        plot = plot_widget.getPlotItem()
        
        # Add a grid
        plot.showGrid(x=True, y=True)
        
        # Create the bar graph
        bar_graph = pg.BarGraphItem(x=[], height=[], width=0.6, brush=config["color"])
        plot.addItem(bar_graph)
        
        # Store the bar graph in the data series
        self.data_series[name]["bar_graph"] = bar_graph
        
        return plot_widget
    
    def _create_gauge(self, name, config):
        """Create a gauge"""
        # Create a custom gauge widget
        gauge = GaugeWidget(
            min_value=config["min_value"],
            max_value=config["max_value"],
            name=config["name"],
            units=config["units"],
            color=config["color"]
        )
        
        # Store the gauge in the data series
        self.data_series[name]["gauge"] = gauge
        
        return gauge
    
    def _close_visualization(self, index):
        """Close a visualization tab"""
        try:
            # Get the tab name
            name = self.tab_widget.tabText(index)
            
            # Remove the data series
            if name in self.data_series:
                del self.data_series[name]
            
            # Remove the tab
            self.tab_widget.removeTab(index)
            
            logger.info(f"Closed visualization: {name}")
        except Exception as e:
            logger.error(f"Error closing visualization: {e}")
    
    def _process_data(self, port, data, timestamp):
        """Process incoming data for visualizations"""
        try:
            # Check each data series
            for name, series in self.data_series.items():
                config = series["config"]
                
                # Check if this data is from the configured port
                if config["port"] != "all" and config["port"] != port:
                    continue
                
                # Try to extract the value using the regex pattern
                if config["pattern"]:
                    match = re.search(config["pattern"], data)
                    
                    if match:
                        # Extract the value
                        try:
                            if match.groups():
                                value = float(match.group(1))
                            else:
                                value = float(match.group(0))
                            
                            # Apply scaling if configured
                            if config.get("scale"):
                                value = value * config["scale"]
                            
                            # Add to the data series
                            timestamp = time.time()
                            series["data"].append((timestamp, value))
                            series["last_update"] = timestamp
                            
                            # Trim the data series if needed
                            if len(series["data"]) > self.max_data_points:
                                series["data"] = series["data"][-self.max_data_points:]
                        except (ValueError, IndexError) as e:
                            logger.debug(f"Error extracting value from match: {e}")
        except Exception as e:
            logger.error(f"Error processing data for visualization: {e}")
    
    def _update_charts(self):
        """Update all charts with the latest data"""
        try:
            for name, series in self.data_series.items():
                config = series["config"]
                data = series["data"]
                
                if not data:
                    continue
                
                # Update based on chart type
                if config["type"] == "line":
                    self._update_line_chart(name, series)
                elif config["type"] == "bar":
                    self._update_bar_chart(name, series)
                elif config["type"] == "gauge":
                    self._update_gauge(name, series)
        except Exception as e:
            logger.error(f"Error updating charts: {e}")
    
    def _update_line_chart(self, name, series):
        """Update a line chart"""
        try:
            line = series.get("line")
            data = series["data"]
            
            if line and data:
                # Extract x and y values
                x_values = [d[0] - data[0][0] for d in data]  # Relative time
                y_values = [d[1] for d in data]
                
                # Update the line
                line.setData(x_values, y_values)
        except Exception as e:
            logger.error(f"Error updating line chart: {e}")
    
    def _update_bar_chart(self, name, series):
        """Update a bar chart"""
        try:
            bar_graph = series.get("bar_graph")
            data = series["data"]
            
            if bar_graph and data:
                # Use the last N values
                n = min(10, len(data))
                recent_data = data[-n:]
                
                # Extract x and y values
                x_values = list(range(len(recent_data)))
                y_values = [d[1] for d in recent_data]
                
                # Update the bar graph
                bar_graph.setOpts(x=x_values, height=y_values)
        except Exception as e:
            logger.error(f"Error updating bar chart: {e}")
    
    def _update_gauge(self, name, series):
        """Update a gauge"""
        try:
            gauge = series.get("gauge")
            data = series["data"]
            
            if gauge and data:
                # Use the most recent value
                value = data[-1][1]
                
                # Update the gauge
                gauge.set_value(value)
        except Exception as e:
            logger.error(f"Error updating gauge: {e}")
    
    def _set_update_interval(self, interval):
        """Set the update interval"""
        try:
            self.update_interval = interval
            self.update_timer.setInterval(interval)
            logger.debug(f"Update interval set to {interval} ms")
        except Exception as e:
            logger.error(f"Error setting update interval: {e}")
    
    def _set_max_data_points(self, max_points):
        """Set the maximum number of data points"""
        try:
            self.max_data_points = max_points
            logger.debug(f"Max data points set to {max_points}")
            
            # Trim existing data series if needed
            for name, series in self.data_series.items():
                if len(series["data"]) > max_points:
                    series["data"] = series["data"][-max_points:]
        except Exception as e:
            logger.error(f"Error setting max data points: {e}")
    
    def _export_data(self):
        """Export visualization data"""
        try:
            # Check if there are any visualizations
            if not self.data_series:
                QMessageBox.information(self, "Export Data", "No visualization data to export.")
                return
            
            # Get the current visualization
            current_index = self.tab_widget.currentIndex()
            current_name = self.tab_widget.tabText(current_index)
            
            # Show a file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Data", "", "CSV Files (*.csv);;JSON Files (*.json)"
            )
            
            if not file_path:
                return
            
            # Determine the export format based on the file extension
            if file_path.endswith(".csv"):
                self._export_csv(file_path, current_name)
            else:
                self._export_json(file_path, current_name)
            
            QMessageBox.information(self, "Export Data", f"Data exported to {file_path}")
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            QMessageBox.critical(self, "Error", f"Error exporting data: {e}")
    
    def _export_csv(self, file_path, name):
        """Export data to a CSV file"""
        try:
            series = self.data_series.get(name)
            
            if not series:
                raise ValueError(f"Visualization not found: {name}")
            
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(["Timestamp", "Value"])
                
                # Write data
                for timestamp, value in series["data"]:
                    # Convert timestamp to readable format
                    dt = datetime.fromtimestamp(timestamp)
                    writer.writerow([dt.strftime("%Y-%m-%d %H:%M:%S.%f"), value])
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            raise
    
    def _export_json(self, file_path, name):
        """Export data to a JSON file"""
        try:
            series = self.data_series.get(name)
            
            if not series:
                raise ValueError(f"Visualization not found: {name}")
            
            # Prepare the data
            export_data = {
                "name": name,
                "config": series["config"],
                "data": []
            }
            
            # Add the data points
            for timestamp, value in series["data"]:
                # Convert timestamp to readable format
                dt = datetime.fromtimestamp(timestamp)
                export_data["data"].append({
                    "timestamp": dt.strftime("%Y-%m-%d %H:%M:%S.%f"),
                    "value": value
                })
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error exporting JSON: {e}")
            raise
    
    def get_visualization_state(self):
        """Get the current state of all visualizations"""
        try:
            state = []
            
            for name, series in self.data_series.items():
                state.append({
                    "name": name,
                    "config": series["config"],
                    # Don't include the actual data, just the configuration
                })
            
            return state
        except Exception as e:
            logger.error(f"Error getting visualization state: {e}")
            return []
    
    def restore_visualization_state(self, state):
        """Restore visualizations from a saved state"""
        try:
            for viz in state:
                self._create_visualization(viz["config"])
            
            logger.info(f"Restored {len(state)} visualizations")
        except Exception as e:
            logger.error(f"Error restoring visualization state: {e}")


class AddVisualizationDialog(QDialog):
    """Dialog for adding a new visualization"""
    
    def __init__(self, parent, app):
        """Initialize the dialog"""
        super().__init__(parent)
        
        self.app = app
        
        # Set dialog properties
        self.setWindowTitle("Add Visualization")
        self.setMinimumWidth(500)
        
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
        
        # Visualization name
        self.name_input = QLineEdit()
        form_layout.addRow("Name:", self.name_input)
        
        # Visualization type
        self.type_combo = QComboBox()
        self.type_combo.addItem("Line Chart", "line")
        self.type_combo.addItem("Bar Chart", "bar")
        self.type_combo.addItem("Gauge", "gauge")
        self.type_combo.currentIndexChanged.connect(self._type_changed)
        form_layout.addRow("Type:", self.type_combo)
        
        # Data source
        self.port_combo = QComboBox()
        self.port_combo.addItem("All Devices", "all")
        
        # Add connected devices
        if hasattr(self.app, 'device_manager'):
            for device in self.app.device_manager.get_connected_devices():
                self.port_combo.addItem(f"{device['name']} ({device['port']})", device['port'])
        
        form_layout.addRow("Data Source:", self.port_combo)
        
        # Pattern for extracting data
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("Regular expression pattern (e.g., 'Temperature: (\\d+\\.\\d+)')")
        form_layout.addRow("Pattern:", self.pattern_input)
        
        # Scaling factor
        self.scale_input = QLineEdit("1.0")
        form_layout.addRow("Scaling Factor:", self.scale_input)
        
        # Chart-specific settings
        self.chart_settings_group = QGroupBox("Chart Settings")
        layout.addWidget(self.chart_settings_group)
        
        self.chart_settings_layout = QFormLayout()
        self.chart_settings_group.setLayout(self.chart_settings_layout)
        
        # X-axis label
        self.x_label_input = QLineEdit("Time")
        self.chart_settings_layout.addRow("X-Axis Label:", self.x_label_input)
        
        # Y-axis label
        self.y_label_input = QLineEdit("Value")
        self.chart_settings_layout.addRow("Y-Axis Label:", self.y_label_input)
        
        # Color
        self.color_combo = QComboBox()
        self.color_combo.addItem("Red", "#FF0000")
        self.color_combo.addItem("Green", "#00FF00")
        self.color_combo.addItem("Blue", "#0000FF")
        self.color_combo.addItem("Yellow", "#FFFF00")
        self.color_combo.addItem("Cyan", "#00FFFF")
        self.color_combo.addItem("Magenta", "#FF00FF")
        self.color_combo.addItem("Orange", "#FFA500")
        self.color_combo.addItem("Purple", "#800080")
        self.chart_settings_layout.addRow("Color:", self.color_combo)
        
        # Gauge-specific settings
        self.gauge_settings_group = QGroupBox("Gauge Settings")
        self.gauge_settings_group.setVisible(False)
        layout.addWidget(self.gauge_settings_group)
        
        self.gauge_settings_layout = QFormLayout()
        self.gauge_settings_group.setLayout(self.gauge_settings_layout)
        
        # Min value
        self.min_value_input = QLineEdit("0")
        self.gauge_settings_layout.addRow("Min Value:", self.min_value_input)
        
        # Max value
        self.max_value_input = QLineEdit("100")
        self.gauge_settings_layout.addRow("Max Value:", self.max_value_input)
        
        # Units
        self.units_input = QLineEdit("")
        self.gauge_settings_layout.addRow("Units:", self.units_input)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _type_changed(self, index):
        """Handle visualization type change"""
        viz_type = self.type_combo.currentData()
        
        # Show/hide gauge settings
        self.gauge_settings_group.setVisible(viz_type == "gauge")
    
    def accept(self):
        """Handle dialog acceptance"""
        try:
            # Validate inputs
            name = self.name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "Validation Error", "Please enter a name for the visualization.")
                return
            
            pattern = self.pattern_input.text().strip()
            if not pattern:
                QMessageBox.warning(self, "Validation Error", "Please enter a pattern for extracting data.")
                return
            
            # Try to compile the pattern
            try:
                re.compile(pattern)
            except re.error as e:
                QMessageBox.warning(self, "Validation Error", f"Invalid regular expression pattern: {e}")
                return
            
            # Validate scaling factor
            try:
                scale = float(self.scale_input.text())
            except ValueError:
                QMessageBox.warning(self, "Validation Error", "Scaling factor must be a number.")
                return
            
            # Validate gauge settings if applicable
            viz_type = self.type_combo.currentData()
            if viz_type == "gauge":
                try:
                    min_value = float(self.min_value_input.text())
                    max_value = float(self.max_value_input.text())
                    
                    if min_value >= max_value:
                        QMessageBox.warning(self, "Validation Error", "Min value must be less than max value.")
                        return
                except ValueError:
                    QMessageBox.warning(self, "Validation Error", "Min and max values must be numbers.")
                    return
            
            # All validation passed
            super().accept()
        except Exception as e:
            logger.error(f"Error validating visualization: {e}")
            QMessageBox.critical(self, "Error", f"Error validating visualization: {e}")
    
    def get_config(self):
        """Get the visualization configuration"""
        try:
            config = {
                "name": self.name_input.text().strip(),
                "type": self.type_combo.currentData(),
                "port": self.port_combo.currentData(),
                "pattern": self.pattern_input.text().strip(),
                "scale": float(self.scale_input.text()),
                "x_label": self.x_label_input.text().strip(),
                "y_label": self.y_label_input.text().strip(),
                "color": self.color_combo.currentData()
            }
            
            # Add gauge-specific settings if applicable
            if config["type"] == "gauge":
                config["min_value"] = float(self.min_value_input.text())
                config["max_value"] = float(self.max_value_input.text())
                config["units"] = self.units_input.text().strip()
            
            return config
        except Exception as e:
            logger.error(f"Error getting visualization config: {e}")
            raise


class GaugeWidget(QWidget):
    """Custom widget for displaying a gauge"""
    
    def __init__(self, min_value=0, max_value=100, name="Gauge", units="", color="#0000FF"):
        """Initialize the gauge widget"""
        super().__init__()
        
        self.min_value = min_value
        self.max_value = max_value
        self.value = min_value
        self.name = name
        self.units = units
        self.color = QColor(color)
        
        # Set minimum size
        self.setMinimumSize(200, 200)
    
    def set_value(self, value):
        """Set the gauge value"""
        # Clamp the value to the range
        self.value = max(self.min_value, min(self.max_value, value))
        
        # Trigger a repaint
        self.update()
    
    def paintEvent(self, event):
        """Paint the gauge"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate the gauge rectangle
        rect = self.rect()
        size = min(rect.width(), rect.height()) - 20
        gauge_rect = QRectF(
            rect.center().x() - size/2,
            rect.center().y() - size/2,
            size,
            size
        )
        
        # Draw the gauge background
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        painter.drawEllipse(gauge_rect)
        
        # Draw the gauge value
        start_angle = 135 * 16  # Start at 135 degrees (7:30 position)
        span_angle = -270 * 16  # Span 270 degrees counter-clockwise
        
        # Calculate the value angle
        value_fraction = (self.value - self.min_value) / (self.max_value - self.min_value)
        value_angle = start_angle + value_fraction * span_angle
        
        # Draw the gauge arc
        painter.setPen(QPen(self.color, 10))
        painter.drawArc(gauge_rect, start_angle, value_angle - start_angle)
        
        # Draw the gauge needle
        painter.setPen(QPen(Qt.GlobalColor.red, 2))
        painter.setBrush(QBrush(Qt.GlobalColor.red))
        
        center = gauge_rect.center()
        needle_length = size / 2 - 10
        
        # Convert angle from 1/16th degrees to radians
        angle_rad = (value_angle / 16) * math.pi / 180
        
        # Calculate needle endpoint
        end_x = center.x() + needle_length * math.cos(angle_rad)
        end_y = center.y() + needle_length * math.sin(angle_rad)
        
        # Draw the needle
        painter.drawLine(center.x(), center.y(), end_x, end_y)
        
        # Draw a circle at the center
        painter.setBrush(QBrush(Qt.GlobalColor.black))
        painter.drawEllipse(center, 5, 5)
        
        # Draw the value text
        painter.setPen(QPen(Qt.GlobalColor.black))
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        
        value_text = f"{self.value:.1f}"
        if self.units:
            value_text += f" {self.units}"
        
        painter.drawText(
            rect.adjusted(0, size/2 + 10, 0, 0),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            value_text
        )
        
        # Draw the name
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        
        painter.drawText(
            rect.adjusted(0, 0, 0, -size/2 - 10),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
            self.name
        )