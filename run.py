#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Hardware Debugger and Serial Monitor
Launcher script
"""

import sys
import os
import subprocess
import platform

def main():
    """Main entry point for the launcher"""
    print("Universal Hardware Debugger and Serial Monitor")
    print("Starting application...")
    
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Check for direct run argument
    direct_run = "--direct" in sys.argv
    
    if direct_run:
        print("Running application directly (skipping virtual environment)...")
        run_application_direct(script_dir)
    else:
        # Check if the virtual environment exists
        venv_dir = os.path.join(script_dir, "venv")
        venv_python = os.path.join(venv_dir, "bin", "python")
        if platform.system() == "Windows":
            venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
        
        if not os.path.exists(venv_python):
            print("Virtual environment not found. Creating...")
            create_venv(script_dir, venv_dir)
        
        # Install requirements if needed
        requirements_file = os.path.join(script_dir, "requirements.txt")
        if os.path.exists(requirements_file):
            print("Installing requirements...")
            install_requirements(venv_python, requirements_file)
        
        # Run the application
        print("Launching application...")
        run_application(venv_python, script_dir)

def create_venv(script_dir, venv_dir):
    """Create a virtual environment"""
    try:
        # Check if venv module is available
        try:
            import venv
        except ImportError:
            print("Python venv module is not available.")
            if platform.system() == "Linux":
                # Check for common Linux distributions
                if os.path.exists("/etc/debian_version") or os.path.exists("/etc/ubuntu_version"):
                    print("\nOn Debian/Ubuntu systems, you need to install the python3-venv package:")
                    print("    sudo apt install python3-venv")
                elif os.path.exists("/etc/fedora-release"):
                    print("\nOn Fedora systems, you need to install the python3-venv package:")
                    print("    sudo dnf install python3-venv")
                elif os.path.exists("/etc/arch-release"):
                    print("\nOn Arch Linux, you need to install the python-virtualenv package:")
                    print("    sudo pacman -S python-virtualenv")
                else:
                    print("\nPlease install the Python venv module for your distribution.")
            elif platform.system() == "Windows":
                print("\nMake sure you have installed Python with the 'pip' and 'venv' options enabled.")
            elif platform.system() == "Darwin":  # macOS
                print("\nOn macOS, you may need to install Python via Homebrew:")
                print("    brew install python")
            
            print("\nAlternatively, you can run the application directly:")
            print(f"    python {os.path.join(script_dir, 'src', 'main.py')}")
            sys.exit(1)
        
        # Create the virtual environment
        venv.create(venv_dir, with_pip=True)
        print("Virtual environment created successfully.")
    except Exception as e:
        print(f"Error creating virtual environment: {e}")
        print("\nYou can try running the application directly:")
        print(f"    python {os.path.join(script_dir, 'src', 'main.py')}")
        print("\nOr manually set up the environment:")
        print("    python -m venv venv")
        if platform.system() == "Windows":
            print("    venv\\Scripts\\activate")
            print("    pip install -r requirements.txt")
            print("    python src\\main.py")
        else:
            print("    source venv/bin/activate")
            print("    pip install -r requirements.txt")
            print("    python src/main.py")
        sys.exit(1)

def install_requirements(venv_python, requirements_file):
    """Install requirements"""
    try:
        subprocess.check_call([venv_python, "-m", "pip", "install", "-r", requirements_file])
        print("Requirements installed successfully.")
    except Exception as e:
        print(f"Error installing requirements: {e}")
        print("Please install the requirements manually.")
        sys.exit(1)

def run_application(venv_python, script_dir):
    """Run the application using the virtual environment"""
    try:
        main_script = os.path.join(script_dir, "src", "main.py")
        subprocess.check_call([venv_python, main_script])
    except Exception as e:
        print(f"Error running application: {e}")
        print("\nTrying to run directly...")
        run_application_direct(script_dir)

def run_application_direct(script_dir):
    """Run the application directly without a virtual environment"""
    try:
        # Install required packages if they're not already installed
        requirements_file = os.path.join(script_dir, "requirements.txt")
        if os.path.exists(requirements_file):
            print("Checking and installing required packages...")
            python_exe = sys.executable
            try:
                # Install the requirements
                print("Installing required packages...")
                subprocess.check_call([python_exe, "-m", "pip", "install", "-r", requirements_file])
                print("Required packages installed successfully.")
            except Exception as e:
                print(f"Error installing packages: {e}")
                print("\nPlease install the required packages manually:")
                print(f"    {python_exe} -m pip install -r {requirements_file}")
                sys.exit(1)
        
        # Run the application
        main_script = os.path.join(script_dir, "src", "main.py")
        
        # Use the current Python interpreter
        python_exe = sys.executable
        subprocess.check_call([python_exe, main_script])
    except Exception as e:
        print(f"Error running application directly: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()