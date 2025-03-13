# Universal Hardware Debugger and Serial Monitor

A cross-platform application for debugging and monitoring multiple microcontrollers simultaneously.

## Features

- Auto-detection of connected microcontrollers via USB
- Real-time serial monitoring with timestamps, filtering, and logging options
- Multi-device support, allowing users to manage multiple boards in separate tabs
- Command sending interface to send AT commands or custom debugging inputs
- Graphical visualization of sensor data (e.g., temperature, humidity, voltage)
- Embedded scripting support to automate debugging and testing tasks

## Supported Microcontrollers

- Arduino (various models)
- ESP32/ESP8266
- Raspberry Pi Pico
- STM32
- Teensy
- Particle devices
- Nordic nRF series
- And more...

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- PyQt6 (for the GUI)
- pyserial (for serial communication)
- pyqtgraph (for data visualization)

### Setup

#### Option 1: Using the launcher script (recommended)

1. Clone this repository:

   ```
   git clone https://github.com/yourusername/universal-hardware-debugger.git
   cd universal-hardware-debugger
   ```

2. Run the launcher script:

   ```
   ./run.py
   ```

   The launcher will automatically:

   - Create a virtual environment
   - Install the required dependencies
   - Start the application

   **Note for Linux users**: You may need to install the python3-venv package:

   ```
   sudo apt install python3-venv  # Debian/Ubuntu
   sudo dnf install python3-venv  # Fedora
   sudo pacman -S python-virtualenv  # Arch Linux
   ```

#### Option 2: Direct run

1. Clone this repository:

   ```
   git clone https://github.com/yourusername/universal-hardware-debugger.git
   cd universal-hardware-debugger
   ```

2. Install the required dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Run the application directly:

   ```
   python src/main.py
   ```

   Or use the launcher with the direct option:

   ```
   ./run.py --direct
   ```

#### Option 3: Manual virtual environment setup

1. Clone this repository:

   ```
   git clone https://github.com/yourusername/universal-hardware-debugger.git
   cd universal-hardware-debugger
   ```

2. Create and activate a virtual environment:

   ```
   python -m venv venv

   # On Windows:
   venv\Scripts\activate

   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install the required dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Run the application:

   ```
   python src/main.py
   ```

## Development

See the [architecture_plan.md](architecture_plan.md) for detailed information about the project structure and components.

## License

MIT
