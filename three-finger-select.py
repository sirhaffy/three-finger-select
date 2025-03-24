import evdev
from evdev import InputDevice, ecodes
import time
from pynput.mouse import Controller, Button
import threading
import sys
import os
import logging
import subprocess

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/three-finger-select.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('three-finger-select')

# Ensure we're running as root
if os.geteuid() != 0:
    logger.error("This script must be run as root!")
    sys.exit(1)

# Ensure the DISPLAY environment variable is set
if 'DISPLAY' not in os.environ:
    logger.info("DISPLAY not set, using default :0")
    os.environ['DISPLAY'] = ':0'

# Log environment variables for debugging
logger.info(f"DISPLAY={os.environ.get('DISPLAY')}")
logger.info(f"XAUTHORITY={os.environ.get('XAUTHORITY')}")
logger.info(f"XDG_RUNTIME_DIR={os.environ.get('XDG_RUNTIME_DIR')}")

# Try to initialize mouse controller with a retry mechanism
mouse = None
max_retries = 5
retry_count = 0

while retry_count < max_retries:
    try:
        mouse = Controller()
        logger.info("Successfully initialized mouse controller")
        break
    except Exception as e:
        retry_count += 1
        logger.error(f"Failed to initialize mouse controller (attempt {retry_count}/{max_retries}): {e}")
        time.sleep(2)  # Wait before retrying

if mouse is None:
    logger.error("Could not initialize mouse controller after multiple attempts")
    sys.exit(1)

# Variabler för att hålla reda på om tre fingrar är aktiva och musens status
three_fingers_active = False
button_pressed = False
click_delay = 0.0025

# Variables for tracking touchpad position and movement
last_x = 0
last_y = 0

# Movement sensitivity - lower value = slower movement
movement_scale = 0.5  # Adjust this value to control speed (0.1-1.0)

# Find touchpad device
def find_touchpad():
    try:
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        logger.info(f"Found {len(devices)} input devices")

        for device in devices:
            logger.info(f"Checking device: {device.name} ({device.path})")
            if "touchpad" in device.name.lower():
                logger.info(f"Found touchpad: {device.name}")
                return device

        # Fallback to any device that might be a touchpad
        for device in devices:
            caps = device.capabilities()
            # Check if it has absolute axes which is typical for touchpads
            if evdev.ecodes.EV_ABS in caps:
                logger.info(f"Found potential touchpad device: {device.name}")
                return device

        logger.error("No touchpad found among available devices")
        return None
    except Exception as e:
        logger.error(f"Error finding touchpad: {e}")
        return None

def listen_for_input():
    global three_fingers_active, button_pressed, last_x, last_y

    try:
        device = find_touchpad()
        if not device:
            logger.error("No touchpad found!")
            return

        logger.info(f"Listening to device: {device.name}")

        finger_count = 0
        current_x = 0
        current_y = 0
        abs_x = 0
        abs_y = 0
        have_x = False
        have_y = False

        # Get device capabilities to calculate movement scaling
        caps = device.capabilities(verbose=True)
        x_min = 0
        x_max = 0
        y_min = 0
        y_max = 0

        # Get the min/max values for X and Y axes if available
        if ecodes.EV_ABS in caps:
            for code, info in caps[ecodes.EV_ABS]:
                if code[0] == 'ABS_X':
                    x_min = info.min
                    x_max = info.max
                    logger.info(f"Found X axis range: {x_min} to {x_max}")
                elif code[0] == 'ABS_Y':
                    y_min = info.min
                    y_max = info.max
                    logger.info(f"Found Y axis range: {y_min} to {y_max}")

        logger.info(f"X range: {x_min} to {x_max}")
        logger.info(f"Y range: {y_min} to {y_max}")

        for event in device.read_loop():
            # Handle finger count changes
            if event.type == ecodes.EV_ABS:
                if event.code == ecodes.ABS_MT_TRACKING_ID:
                    if event.value == -1:  # Finger lifted
                        finger_count = max(0, finger_count - 1)
                    else:  # New finger touch
                        finger_count += 1

                # Track absolute position for cursor movement
                elif event.code == ecodes.ABS_X:
                    abs_x = event.value
                    have_x = True
                elif event.code == ecodes.ABS_Y:
                    abs_y = event.value
                    have_y = True

                # If we have both X and Y coordinates, calculate movement
                if have_x and have_y:
                    if three_fingers_active and button_pressed:
                        # Calculate relative movement
                        rel_x = abs_x - last_x
                        rel_y = abs_y - last_y

                        # Apply movement scaling to slow down cursor
                        rel_x = rel_x * movement_scale
                        rel_y = rel_y * movement_scale

                        # Only move if there's a significant change
                        if abs(rel_x) > 0.5 or abs(rel_y) > 0.5:
                            try:
                                # Get current position and apply the movement
                                current_pos = mouse.position
                                # Convert to integer for mouse position
                                new_x = int(current_pos[0] + rel_x)
                                new_y = int(current_pos[1] + rel_y)
                                mouse.position = (new_x, new_y)
                            except Exception as e:
                                logger.error(f"Error moving mouse: {e}")

                    # Update last position
                    last_x = abs_x
                    last_y = abs_y
                    have_x = False
                    have_y = False

            # Handle three finger gestures state
            if finger_count == 3 and not three_fingers_active:
                logger.info("Three fingers detected")
                three_fingers_active = True
                time.sleep(click_delay)
                try:
                    mouse.press(Button.left)
                    button_pressed = True
                    # Store initial position
                    last_x = abs_x
                    last_y = abs_y
                except Exception as e:
                    logger.error(f"Error pressing mouse button: {e}")

            elif finger_count < 3 and three_fingers_active:
                logger.info("Fingers lifted")
                three_fingers_active = False
                if button_pressed:
                    try:
                        mouse.release(Button.left)
                        button_pressed = False
                    except Exception as e:
                        logger.error(f"Error releasing mouse button: {e}")

    except Exception as e:
        logger.error(f"Error in listen_for_input: {e}")
        return

# Main thread
try:
    logger.info("Starting three-finger-select")
    listener_thread = threading.Thread(target=listen_for_input)
    listener_thread.daemon = True
    listener_thread.start()

    # Keep script running
    logger.info("Main thread running")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    logger.info("Program interrupted by user")
except Exception as e:
    logger.error(f"Unexpected error in main thread: {e}")
    sys.exit(1)