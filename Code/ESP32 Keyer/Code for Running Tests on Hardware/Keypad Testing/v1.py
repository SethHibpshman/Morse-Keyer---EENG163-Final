from machine import Pin
from keypad import Keypad
from time import sleep, ticks_ms, ticks_diff

# GPIO pins
row_pins = [Pin(5), Pin(6), Pin(15), Pin(17)]
column_pins = [Pin(18), Pin(2), Pin(39), Pin(40)]

# Keypad layout
keys = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']
]

keypad = Keypad(row_pins, column_pins, keys)

# Keypad Initialization ####################################
# Button Press Counter #################
keypad_button_counts = {}
for ii in keys:                       # For each list in keys[]
    for i in ii:                      # For each character in the list of keys[[]]
        keypad_button_counts[i] = 0   # i is the key, 0 is the value.

# Button Previous State Tracker ########
keypad_button_prev_states = {}
for ii in keys:
    for i in ii:
        keypad_button_prev_states[i] = False

# Keypad Multi-Tap Map #################
keypad_multi_tap_map = {
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
keypad_idle_start_time = 0
keypad_idle_time = 0

# State Tracking
active_key = None
tap_count = 0
last_press_time = 0
multi_tap_timeout = 1000  # ms
output_text = ""
control_keys = {'*', '#', 'A', 'B', 'C', 'D', '1'}

def keypad_handler(key_pressed):
    global active_key, tap_count, last_press_time, current_time, keypad_idle_start_time

    key = key_pressed[0]

    # Any key press → not idle
    keypad_idle_start_time = 0

    # Edge detection
    if not keypad_button_prev_states[key]:

        # 🔹 CONTROL KEY BLOCK (no multi-tap) 🔹
        if key in control_keys:
            commit_active_key()  # finish any pending letter

            handle_control_key(key)  # do custom action

            keypad_button_prev_states[key] = True
            return

        # 🔹 MULTI-TAP LETTER KEYS 🔹
        if key == active_key and ticks_diff(current_time, last_press_time) < multi_tap_timeout:
            tap_count = tap_count + 1
            overwrite_last_character()
        else:
            commit_active_key()

            active_key = key
            tap_count = 1
            append_new_character()

        last_press_time = current_time
        keypad_button_prev_states[key] = True

def keypad_idle_checker():
    global keypad_idle_start_time, current_time, keypad_idle_time, active_key

    # Only track idle if a key sequence is in progress
    if active_key is None:
        return

    # Track time. If 1 second passes, finalize letter. if pressed again, reset timer. If other key pressed, finalize previous letter.
    # If no activity on buttons...
    if keypad_idle_start_time == 0:
        # And if not currently counting the idle time, start counting it.
        keypad_idle_start_time = current_time

    keypad_idle_time = ticks_diff(current_time, keypad_idle_start_time) # Updates how long it's been idle.

    if keypad_idle_time >= multi_tap_timeout:
        commit_active_key()
        keypad_idle_start_time = 0

def commit_active_key():
    global active_key, tap_count

    # Nothing to commit
    if active_key is None:
        return

    active_key = None
    tap_count = 0

def append_new_character():
    global output_text

    if active_key in keypad_multi_tap_map:
        letters = keypad_multi_tap_map[active_key]
        index = (tap_count - 1) % len(letters)
        letter = letters[index]
    else:
        letter = active_key

    output_text = output_text + letter
    print("\r" + output_text, end="")

def overwrite_last_character():
    global output_text

    if len(output_text) == 0:
        return

    if active_key in keypad_multi_tap_map:
        letters = keypad_multi_tap_map[active_key]
        index = (tap_count - 1) % len(letters)
        letter = letters[index]
    else:
        letter = active_key

    # Replace last character
    output_text = output_text[:-1] + letter
    print("\r" + output_text, end="")

def handle_control_key(key):
    global output_text

    if key == '*':
        print("Pressed: *")

    elif key == '#':
        print("Pressed: *")

    elif key == 'A':
        # Backspace
        if len(output_text) > 0:
            output_text = output_text[:-1]
            print(output_text)

    elif key == 'B':
        print("Pressed: B")

    elif key == 'C':
        print("Pressed: C")

    elif key == 'D':
        print("Pressed: D")

    elif key == '1':
        print("Pressed: 1")

# Main loop
while True:
    current_time = ticks_ms()

    # Keypad Stuff ####################################
    pressed_keys = keypad.read_keypad()  # returns a list of pressed keys (using the keypad library)

    # Handle current pressed keys #####################
    if pressed_keys:
        keypad_handler(pressed_keys)
    else:
        keypad_idle_checker()

    # Reset keys that are no longer pressed ###########
    for i in keypad_button_prev_states:
        if not pressed_keys or i not in pressed_keys: # If no keys are pressed or if a key that was previously true is not pressed.
            keypad_button_prev_states[i] = False

    sleep(0.05)  # Debounce