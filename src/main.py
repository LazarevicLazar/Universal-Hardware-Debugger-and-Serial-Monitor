#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Main entry point for the application
"""

import sys
import os
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Create application data directory if it doesn't exist
app_data_dir = Path.home() / '.universal_debugger'
app_data_dir.mkdir(exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(app_data_dir / 'app.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the application"""
    try:
        
        # Import here to avoid circular imports
        from src.core.app import Application
        
        # Create and run the application
        app = Application(sys.argv)
        sys.exit(app.exec())
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()