# #######################
# Project Name: 12-key numeric keypad using 4x4 membrane keypad
# Date: 02/23/2026
# Name: Seth Hibpshman
# Collaborators:
#       PerfecXX - MicroPython-SimpleKeypad Library
# #######################

from machine import Pin
from keypad import Keypad
from time import sleep, ticks_ms, ticks_diff

# <><><><><><><><><><><><><><><><><><><><><><>
# SETUP
# <><><><><><><><><><><><><><><><><><><><><><>

# HARDWARE ##############################
    # Keypad
keypad_gpio_row_pins = [Pin('PA1'), Pin('PA2'), Pin('PA3'), Pin('PA4')]
keypad_gpio_column_pins = [Pin('PB1'), Pin('PB2'), Pin('PB3'), Pin('PB4')]
    # Keypad layout mapping
keypad_layout_keys = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']]
keypad_device = Keypad(keypad_gpio_row_pins, keypad_gpio_column_pins, keypad_layout_keys)
# Force all column pins HIGH (required on STM32)
for col in keypad_device.column_pins:
    col.value(1)

# SOFTWARE ##############################
    # Key Press Counters #################
'''A dictionary that stores how many times each key has been pressed.'''
keypad_button_press_counters = {}
for keypad_row in keypad_layout_keys:            # For each list in keys[]
    for keypad_key in keypad_row:               # For each key in that row
        keypad_button_press_counters[keypad_key] = 0   # Initialize count to 0

    # Previous Key Press State Tracker ########
    '''A dictionary that stores if a button is pressed or not.'''
keypad_button_previous_states = {}
for keypad_row in keypad_layout_keys:
    for keypad_key in keypad_row:
        keypad_button_previous_states[keypad_key] = False

    # Keypad Multi-Tap Mapping #################
keypad_multi_tap_letter_map = {
    '2': ['A', 'B', 'C'],
    '3': ['D', 'E', 'F'],
    '4': ['G', 'H', 'I'],
    '5': ['J', 'K', 'L'],
    '6': ['M', 'N', 'O'],
    '7': ['P', 'Q', 'R', 'S'],
    '8': ['T', 'U', 'V'],
    '9': ['W', 'X', 'Y', 'Z'],
    '0': [' ']
}

    # Idle timer tracking ###################
keypad_idle_start_time_ms = 0
keypad_idle_elapsed_time_ms = 0

    # State Tracking
keypad_active_key = None
keypad_tap_count = 0
keypad_last_press_time_ms = 0
keypad_multi_tap_timeout_ms = 1000
keypad_output_text = ""
keypad_control_keys = {'*', '#', 'A', 'B', 'C', 'D', '1'}

    # For periodic printing
keypad_output_print_interval_ms = 200
keypad_last_output_print_time_ms = 0

# <><><><><><><><><><><><><><><><><><><><><><>
# FUNCTIONS
# <><><><><><><><><><><><><><><><><><><><><><>

def keypad_handle_pressed_keys(pressed_keys):
    """
    Processes a newly detected key press using edge detection.

    Handles two paths:
    - Control keys: commits any pending multi-tap character and executes the
      mapped control action (e.g., backspace).
    - Multi-tap keys: updates the tap count if the same key is pressed within
      the timeout window, otherwise commits the previous character and starts
      a new multi-tap sequence.

    Also resets the idle timer and updates the last press timestamp.
    """
    global keypad_active_key, keypad_tap_count, keypad_last_press_time_ms, current_time, keypad_idle_start_time_ms

    keypad_current_key = pressed_keys[0]  # Only process one key at a time
    keypad_idle_start_time_ms = 0  # Reset idle timer on any key press

    # Edge detection to detect new press
    if not keypad_button_previous_states[keypad_current_key]:

        # CONTROL KEY BLOCK (no multi-tap) #######
        if keypad_current_key in keypad_control_keys:
            keypad_commit_active_key()  # Commit any pending letter
            keypad_handle_control_key(keypad_current_key)  # Do custom action
            keypad_button_previous_states[keypad_current_key] = True
            return

        # MULTI-TAP LETTER KEYS ##################
        if (keypad_current_key == keypad_active_key and ticks_diff(current_time, keypad_last_press_time_ms) < keypad_multi_tap_timeout_ms):
            keypad_tap_count += 1
            keypad_overwrite_last_character()
        else:  # First press of a new key
            keypad_commit_active_key()
            keypad_active_key = keypad_current_key
            keypad_tap_count = 1
            keypad_append_new_character()

        keypad_last_press_time_ms = current_time
        keypad_button_previous_states[keypad_current_key] = True

def keypad_idle_time_checker():
    """
    Monitors elapsed idle time while a multi-tap key is active.

    Starts an idle timer after the last press and, once the timeout is reached,
    commits the currently active multi-tap character and clears the active key
    state so the next press begins a new character.
    """
    global keypad_idle_start_time_ms, current_time, keypad_idle_elapsed_time_ms, keypad_active_key
    if keypad_active_key is None:  # Nothing to check if no key is active
        return

    if keypad_idle_start_time_ms == 0:  # Initialize idle timer if not already started
        keypad_idle_start_time_ms = current_time

    keypad_idle_elapsed_time_ms = ticks_diff(current_time, keypad_idle_start_time_ms)

    if keypad_idle_elapsed_time_ms >= keypad_multi_tap_timeout_ms:
        keypad_commit_active_key()
        keypad_idle_start_time_ms = 0

def keypad_commit_active_key():
    """
    Finalizes the current multi-tap character.

    Clears the active key and tap count so subsequent key presses are treated
    as a new character sequence.
    """
    global keypad_active_key, keypad_tap_count
    if keypad_active_key is None:
        return
    keypad_active_key = None
    keypad_tap_count = 0

def keypad_append_new_character():
    """
    Appends a new character to the output string based on the active key and
    current tap count.

    Uses the multi-tap mapping to determine which letter corresponds to the
    first press of a key.
    """
    global keypad_output_text
    if keypad_active_key is None:
        return
    letter = keypad_get_letter_for_keypad_key(keypad_active_key, keypad_tap_count)
    keypad_output_text += letter

def keypad_overwrite_last_character():
    """
    Replaces the most recently appended character with the next letter in the
    multi-tap cycle for the active key.

    Used when the same key is pressed again within the timeout window to cycle
    through its mapped characters.
    """
    global keypad_output_text
    if len(keypad_output_text) == 0 or keypad_active_key is None:
        return
    letter = keypad_get_letter_for_keypad_key(keypad_active_key, keypad_tap_count)
    keypad_output_text = keypad_output_text[:-1] + letter

def keypad_get_letter_for_keypad_key(key, tap_count):
    """
    Returns the character associated with a key and tap count.

    For multi-tap keys, cycles through the mapped letter list using modular
    arithmetic so repeated presses wrap around. For non-mapped keys, returns
    the key itself.
    """
    if key in keypad_multi_tap_letter_map:
        letters = keypad_multi_tap_letter_map[key]
        index = (tap_count - 1) % len(letters)
        return letters[index]
    else:
        return key

def keypad_handle_control_key(key):
    """
    Executes the action associated with a control key.

    Supports operations such as backspace (A) and debug prints for other
    control keys. Does not participate in multi-tap behavior.
    """
    global keypad_output_text

    if key == '*':
        print("Pressed: *")

    elif key == '#':
        print("Pressed: #")

    elif key == 'A':
        # Backspace
        if len(keypad_output_text) > 0:
            keypad_output_text = keypad_output_text[:-1]
            print(keypad_output_text)

    elif key == 'B':
        print("Pressed: B")

    elif key == 'C':
        print("Pressed: C")

    elif key == 'D':
        print("Pressed: D")

    elif key == '1':
        print("Pressed: 1")

# <><><><><><><><><><><><><><><><><><><><><><>
# MAIN LOOP
# <><><><><><><><><><><><><><><><><><><><><><>

while True:
    current_time = ticks_ms() # Updates current time

    pressed_keypad_keys = keypad_device.read_keypad()  # Returns a list of pressed keys

    if pressed_keypad_keys: # Handle pressed keys, if nothing pressed, start the idle timer.
        keypad_handle_pressed_keys(pressed_keypad_keys)
    else:
        keypad_idle_time_checker()

    # Reset keys that are no longer pressed ###########
    for keypad_key in keypad_button_previous_states:
        if not pressed_keypad_keys or keypad_key not in pressed_keypad_keys:
            keypad_button_previous_states[keypad_key] = False

    # Periodic printing of the output string ###########
    if ticks_diff(current_time, keypad_last_output_print_time_ms) >= keypad_output_print_interval_ms:
        print(keypad_output_text)
        keypad_last_output_print_time_ms = current_time

    sleep(0.01)  # Debounce delay
