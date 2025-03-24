# Three Finger Select

A Linux utility that enables three-finger selection gestures on touchpads. This script allows you to select text by touching your touchpad with three fingers and dragging.

Created with the help of AI.

This is mostly for myself so I can reuse it later.. 

## Features

- Select text using three-finger gestures (like MacOS).
- Works with most Linux touchpads.
- Adjustable movement sensitivity.
- Automatic detection of touchpad devices.

## Requirements

- Python 3
- `evdev` Python library
- `pynput` Python library
- Root privileges (for accessing input devices)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/sirhaffy/three-finger-select.git
cd three-finger-select

Install dependencies:
pip install evdev pynput
```

2. Make the scripts executable:
```bash
chmod +x three-finger-select.py
chmod +x start-three-finger.sh
```

3. Configure sudo permissions:
```bash
sudo visudo -f /etc/sudoers.d/three-finger-select

# Add this line (replace username with your username):
username ALL=(ALL) NOPASSWD: /usr/bin/python3 /path/to/three-finger-select.py
```

4. Set up autostart:
```bash
mkdir -p ~/.config/autostart
cp three-finger-select.desktop ~/.config/autostart/
```

5. Usage
The script will start automatically when you log in. You can also run it manually:
```bash
./start-three-finger.sh
```

