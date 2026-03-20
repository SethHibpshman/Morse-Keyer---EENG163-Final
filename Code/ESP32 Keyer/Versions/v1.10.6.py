from machine import Pin, SoftI2C, PWM, reset
from keypad import Keypad
import ssd1306
import gfx
from time import sleep, ticks_ms, ticks_diff

# <><><><><><><><><><><><><><><><><><><><><><>
# SETUP
# <><><><><><><><><><><><><><><><><><><><><><>

# HARDWARE ##############################
# Buzzer
buz = PWM(Pin(1))
buz.freq(700)
buz.duty_u16(0)
buz_vol_list = [0, 500, 1200, 2500, 5000, 9000, 15000, 23000, 33000, 46000, 58000]

# Buttons
dit_in = Pin(16, Pin.IN, Pin.PULL_UP)
dah_in = Pin(7, Pin.IN, Pin.PULL_UP)

# Keypad
keypad_gpio_row_pins = [Pin(5), Pin(6), Pin(15), Pin(17)]
keypad_gpio_column_pins = [Pin(18), Pin(2), Pin(39), Pin(40)]
    # Keypad layout mapping
keypad_layout_keys = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']]
keypad_device = Keypad(keypad_gpio_row_pins, keypad_gpio_column_pins, keypad_layout_keys)
# Keypad software setup
    # Key Press Counters #################
keypad_button_press_counters = {}
for keypad_row in keypad_layout_keys:            # For each list in keys[]
    for keypad_key in keypad_row:               # For each key in that row
        keypad_button_press_counters[keypad_key] = 0   # Initialize count to 0
    # Previous Key Press State Tracker ########
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
keypad_output_print_interval_ms = 1000
keypad_last_output_print_time_ms = 0


# Rotary Encoder
clk = Pin(4, Pin.IN, Pin.PULL_UP)
dt  = Pin(47, Pin.IN, Pin.PULL_UP)
sw  = Pin(45, Pin.IN, Pin.PULL_UP)
last_clk = clk.value()
rotary_hold_start = 0       # Variable to measure how long the rotary encoder button is held.
settings_menu_open = False  # Tracks if settings menu is open. Starts closed.

# External LED
led = Pin(38, Pin.OUT)

# SSD1306 screen setup
i2c = SoftI2C(scl=Pin(46), sda=Pin(8)) 
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
oled_gfx = gfx.GFX(128, 64, oled.pixel)

# SETTINGS MENU
settings_menu_items = [
    # What is to be displayed, and what type it is. If it's a heading, it'll skip scrolling and editing.
    # If not, it'll use that variable as a key to the settings dictionary
    ("MODAL CONFIG", "heading"),
    ("Mode", "mode"),
    ("BEHAVIOR", "heading"),
    ("Keying Mode", "keying_mode"),
    ("Volume", "volume"),
    ("LED", "led"),
    ("Decoding", "decoding"),
    ("OTHER", "heading"),
    ("About", "about"),
    ("Reset", "reset"),
]
settings = { # Values corisponding to each menu item. These are default values.
    "wpm": 10,
    "mode": 2,
    "volume": 5,
    "led": True,
    "keying_mode": 0,
    "decoding": True,
}
settings_menu_selected = 0            # Currently highlighted menu item. Starts at index 0.
settings_menu_scroll = 0              # Vertical text offset (scrolling). Represents the top most menu item index.
settings_menu_line_height = 10        # in pixels
settings_menu_max_visible_lines = 6
settings_menu_in_scrollable_menu = 0  # In scrolling mode of the settings menu. Zero and one because they are easy to compare and save memory.
settings_menu_in_editing_menu = 1                         # In editing menu of the settings menu.
settings_menu_current_menu_mode = settings_menu_in_scrollable_menu  # start in scroll mode

about_scroll_offset = 0  # How much the screen has scrolled through the text lines.
about_scroll_speed = 8   # pixels per update

# SOFTWARE ##############################
# Display Perameters
morse_oled_content = '' # Object where all morse code keyed is held
decoded_text = ''
max_characters = 16 # How many morse characters will be printed on the OLED. 16 is max width of SSD1306

# <><><><><><><><><><><><><><><><><><><><><><>
# FUNCTIONS
# <><><><><><><><><><><><><><><><><><><><><><>

def do_a_dit():
    global morse_oled_content, last_morse_end_time
    buz.duty_u16(buz_volume)
    led.value(settings["led"])  # Reads dictionary to see if the LED is enabled.
    morse_oled_content = morse_oled_content + '.' # Adds a dit to the end of the orse_oled_content string.
    draw_sandbox_mode(morse_oled_content)
    sleep(dit_t)
    buz.duty_u16(0)
    led.value(0)
    sleep(gap_t)
    last_morse_end_time = ticks_ms()

def do_a_dah():
    global morse_oled_content, last_morse_end_time
    buz.duty_u16(buz_volume)
    led.value(settings["led"])
    morse_oled_content = morse_oled_content + '-' # Adds a dah to the end of the orse_oled_content string.
    draw_sandbox_mode(morse_oled_content)
    sleep(dah_t)
    buz.duty_u16(0)
    led.value(0)
    sleep(gap_t)
    last_morse_end_time = ticks_ms()

def play_morse_string(morse_str):
    global morse_oled_content, decoded_text
    n = len(morse_str)
    for i, symbol in enumerate(morse_str):
        last_symbol = (i == n - 1)

        if symbol == '.':
            do_a_dit()
        elif symbol == '-':
            do_a_dah()
        elif symbol == ' ':
            # Letter break
            morse_decoder()
            morse_oled_content += ' '
            draw_sandbox_mode(morse_oled_content)
            sleep(letter_break_t)
        elif symbol == '/':
            # Word break
            morse_decoder()
            morse_oled_content += '/'
            decoded_text += ' '
            draw_sandbox_mode(morse_oled_content)
            sleep(word_break_t)

        # If this is the last symbol, treat it as a word break
        if last_symbol:
            morse_decoder()
            morse_oled_content += '/'
            decoded_text += ' '
            draw_sandbox_mode(morse_oled_content)
            sleep(word_break_t)

def draw_centered(text, center_x, y):
    width = len(text) * 8
    x = center_x - (width // 2)
    oled.text(text, x, y)

def draw_right_aligned(text, right_x, y):
    width = len(text) * 8  # 8 pixels per character
    x = right_x - width
    oled.text(text, x, y)

def draw_sandbox_mode(morse_oled_content=None):
    oled.fill(0)
    if morse_oled_content is not None:
        oled.text('Morse:', 0, 0)
        draw_right_aligned((morse_oled_content[-max_characters:]), 128, 12)
        if settings["decoding"] == True:
            draw_right_aligned((decoded_text[-max_characters:]), 128, 24)
    oled.show()

def draw_keyboard_replay_mode(keypad_text, morse_text):
    oled.fill(0)
    oled.text('Morse:', 0, 0)
    draw_right_aligned(morse_text[-max_characters:], 128, 12)
    oled.text('Alph. Input:', 0, 24)
    oled.text(keypad_text[-max_characters:], 0, 36)
    oled.show()

def device_reset():
    for i in range(0, 4):
        oled.fill(0)
        draw_centered("Resetting" + "." * i, 64, 28)
        oled.show()
        sleep(0.5)
    reset()

def settings_menu_draw_menu():
    oled.fill(0)
    global settings_menu_scroll

    # EDITING MENU ########################
    if settings_menu_current_menu_mode == settings_menu_in_editing_menu:
        # Extract information needed to display like the item and the value stored in the item
        item = settings_menu_items[settings_menu_selected]
        label = item[0]
        key = item[1]

        if key not in ["heading", "about", "reset"]:  # Do not edit these items
            value_of_currently_selected_menu_item = value_to_str(key, settings[key])
            draw_centered(label, 64, 18)
            draw_centered(value_of_currently_selected_menu_item, 64, 36)
        elif key == "about":
            draw_about_screen()
        elif key == "reset":
            device_reset()
        oled.show()
        return

    # SCROLLABLE SETTINGS MAIN MENU  ########################
    # Handling the top level heading not being hidden.
    extra_heading_line = 0 # 'How many extra lines above the selected should be visible'.
    if settings_menu_selected == 1: # First editable setting under a heading is at index 1 (Mode).
        extra_heading_line = 1 # If Mode selected, also show the heading above it.

    if settings_menu_selected < settings_menu_scroll + extra_heading_line: # If the menu item selected's index is smaller than the top level displayed item...
        settings_menu_scroll = settings_menu_selected - extra_heading_line # Set the top rendered item to the selected item.
    elif settings_menu_selected >= settings_menu_scroll + settings_menu_max_visible_lines: # If the selected's index is greater than the bottom most item (top index + max lines)...
        settings_menu_scroll = settings_menu_selected - settings_menu_max_visible_lines + 1 # Add one to the scrolling index.

    # SETTINGS MENU RENDERING ################################
    # Only iterate over menu items that should be visible. (Starting at the top scrolling index and ending with that plus visible lines OR the end of the menu)
    for i in range(settings_menu_scroll, min(settings_menu_scroll + settings_menu_max_visible_lines, len(settings_menu_items))):
        pixel_y = (i - settings_menu_scroll) * settings_menu_line_height # Row number times the line height.
        if pixel_y + settings_menu_line_height > 64: # NO CLIPPING!!! If the line is to be drawn past the 64 height of the screen, skip it!
            continue
        # Extract information needed to display like the item and the value stored in the item
        item = settings_menu_items[i]
        label = item[0]
        key = item[1]

        if key == "heading":
            oled.text(label, 4, pixel_y + 1, 1)
            oled_gfx.fill_rect(4, pixel_y + 9, len(label) * 8, 1, 1) # The heading underline
        else:
            if i == settings_menu_selected: # Highlight the currently selected.
                oled_gfx.fill_rect(0, pixel_y + 1, 128, settings_menu_line_height - 2, 1) # Highlights in white
                oled.text(label, 12, pixel_y + 1, 0) # Redraws text in black
            else:
                oled.text(label, 12, pixel_y + 1, 1) # Draw in white
    oled.show()

def draw_about_screen():
    global about_scroll_offset
    oled.fill(0)
    credits = [
        "Scroll!",
        "",
        "",
        "",
        "Morse Keyer &" ,
        "Trainer",
        "",
        "Created by:",
        "Seth Hibpshman",
        "",
        "EENG 163",
        "Final Project",
        "",
        "Course",
        "Instructor:",
        "S. Rieseberg",
        "",
        "Software:",
        "- MicroPython",
        "- SSD1306 Lib",
        "  - GFX Lib",
        "- PyCharm",
        "- Thonny",
        "",
        "Special Thanks:",
        "- Supporters",
        "- Open Source",
        "  Community",
        "- Instructors",
        "- Family &",
        "  Friends",
        "",
        "License:",
        "GNU GPL v3",
        "",
        "",
        "",
        "The End <3 :)",
    ]

    total_height = len(credits) * 8
    y_start = 64 - 8 - about_scroll_offset  # start offscreen at bottom (-8 for one line shown initially)

    for line_number, line_content in enumerate(credits): # Enumerate creates an index for each item in the list (each line number).
        y = y_start + line_number * 8
        if -8 < y < 64:  # Don't draw or care about anything that's not visible.
            oled.text(line_content, 0, y, 1)
    oled.show()
    about_scroll_offset = about_scroll_offset + about_scroll_speed # Every time the function is called, scroll whatever the scroll speed is set to.
    # Loop scrolling.
    if about_scroll_offset > total_height + 64:
        about_scroll_offset = 0

def morse_decoder():
    global decoded_text
    # Find the last word or letter separator in the Morse OLED content
    index_last_slash = morse_oled_content.rfind('/')   # Last word break
    index_last_space = morse_oled_content.rfind(' ')   # Last letter break
    last_break_index = max(index_last_slash, index_last_space)  # Use whichever is later

    # Extract the last Morse "letter" (everything after the last separator)
    last_morse_letter = morse_oled_content[last_break_index+1:].strip()  # Remove any accidental whitespace

    if last_morse_letter:  # Only decode if there is actually a Morse character
        if morse_alph_dictionary.get(last_morse_letter):  # Check if it exists in dictionary
            decoded_text = decoded_text + morse_alph_dictionary[last_morse_letter]  # Append decoded letter
        else:
            decoded_text = decoded_text + '?'  # Unknown Morse sequence → show ?

def morse_encoder():
    morse_out = ''
    for ch in keypad_output_text:
        if ch == ' ':
            morse_out = morse_out + '/'  # Word separator
        else:
            morse_out = morse_out + alph_morse_dictionary.get(ch, '?') + ' '
    return morse_out.strip()

def gap_checker():
    global morse_oled_content, idle_start_time, letter_space_happened, word_space_happened, decoded_text
    if dit_val == False and dah_val == False:
        # If no activity on buttons...
        if idle_start_time == 0:
            # And if not currently counting the idle time, start counting it.
            idle_start_time = current_time
        idle_time = ticks_diff(current_time, idle_start_time) # Updates how long it's been idle.

        # (Convert letter_break_t to milliseconds)
        # If the idle time exceeds the letter break perameter and a space hasn't already been printed, print one.
        if idle_time >= int(letter_break_t * 1000) and letter_space_happened == False:
            morse_decoder()
            morse_oled_content = morse_oled_content + ' '
            draw_sandbox_mode(morse_oled_content)
            letter_space_happened = True
            word_space_happened = False

        # WORD GAP counts time since last letter space
        if letter_space_happened == True and word_space_happened == False:
            if idle_time >= int((word_break_t) * 1000):
                # Edits the space to be a slash if the idle is longer than a word break.
                if morse_oled_content and morse_oled_content[-1] == ' ':
                    morse_oled_content = morse_oled_content[:-1] + '/'
                    decoded_text = decoded_text + ' '
                draw_sandbox_mode(morse_oled_content)
                word_space_happened = True
    else:
        # If buttons being pressed, then no breaks, and say it's not idle.
        idle_start_time = 0
        letter_space_happened = False
        word_space_happened = False

def value_to_str(key, menu_value):
    # Some menu items are bools, str, or ints. Converts all to strings.
    if key == "mode":
        return modes[menu_value]
    if key == "keying_mode":
        return keying_modes[menu_value]
    if key in ["led", "decoding"]:
        return "Enabled" if menu_value else "Disabled"
    return str(menu_value)

def rotary_encoder_handler(delta):
    global settings_menu_selected
    # SCROLLABLE SETTINGS MAIN MENU  ########################
    if settings_menu_current_menu_mode == settings_menu_in_scrollable_menu:
        # Move selection until a selectable item is found
        next_index = settings_menu_selected
        while True:
            next_index = (next_index + delta) % len(settings_menu_items) # Moves up/down with delta, also wraps with modulo.
            key = settings_menu_items[next_index][1] # Extracts the key of the next index
            if key not in ["heading"]:  # skip headings, but allow action items like about/reset
                break
        settings_menu_selected = next_index # After a valid item is found, update the selected state

    # EDITING MENU ###########################################
    elif settings_menu_current_menu_mode == settings_menu_in_editing_menu:
        item = settings_menu_items[settings_menu_selected]
        key = item[1]

        # If the key is not one of these, it is not editable. (Ignores items like 'about' and 'reset')
        if key not in ["mode", "keying_mode", "volume", "led", "decoding", "wpm"]:
            return

        menu_value = settings[key]
        if key == "wpm":
            settings[key] = min(max(10, menu_value + delta), 40) # WPM 10-40
        elif key == "volume":
            settings[key] = min(max(0, menu_value + delta), 10) # Volume 0-10
        elif key in ["led", "decoding"]:
            if delta != 0:
                settings[key] = not menu_value # Toggle booleans
        elif key == "mode":
            settings[key] = (menu_value + delta) % len(modes) # Change list index
        elif key == "keying_mode":
            settings[key] = (menu_value + delta) % len(keying_modes) # Change list index

# KEYPAD FUNCTIONS <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
def keypad_handle_pressed_keys(pressed_keys):
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
        if (keypad_current_key == keypad_active_key and
            ticks_diff(current_time, keypad_last_press_time_ms) < keypad_multi_tap_timeout_ms):
            keypad_tap_count = keypad_tap_count + 1
            keypad_overwrite_last_character()
        else:  # First press of a new key
            keypad_commit_active_key()
            keypad_active_key = keypad_current_key
            keypad_tap_count = 1
            keypad_append_new_character()

        keypad_last_press_time_ms = current_time
        keypad_button_previous_states[keypad_current_key] = True

def keypad_idle_time_checker():
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
    global keypad_active_key, keypad_tap_count
    if keypad_active_key is None:
        return
    keypad_active_key = None
    keypad_tap_count = 0

def keypad_append_new_character():
    global keypad_output_text
    if keypad_active_key is None:
        return
    letter = keypad_get_letter_for_keypad_key(keypad_active_key, keypad_tap_count)
    keypad_output_text = keypad_output_text + letter

def keypad_overwrite_last_character():
    global keypad_output_text
    if len(keypad_output_text) == 0 or keypad_active_key is None:
        return
    letter = keypad_get_letter_for_keypad_key(keypad_active_key, keypad_tap_count)
    keypad_output_text = keypad_output_text[:-1] + letter

def keypad_get_letter_for_keypad_key(key, tap_count):
    if key in keypad_multi_tap_letter_map:
        letters = keypad_multi_tap_letter_map[key]
        index = (tap_count - 1) % len(letters)
        return letters[index]
    else:
        return key

def keypad_handle_control_key(key):
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
        morse_str = morse_encoder()  # Convert current keypad output to Morse
        play_morse_string(morse_str)

    elif key == 'C':
        print("Pressed: C")

    elif key == 'D':
        print("Pressed: D")

    elif key == '1':
        print("Pressed: 1")

# Handles keying behavior depending on selected keying mode.
def keying_handler(dit_val, dah_val, current_time):
    global last_d
    global bth_hld, bth_hld_prev
    global dit_hold_start_time, dah_hold_start_time
    global dit_held, dah_held
    global dit_release_time, dah_release_time

    keying_mode = keying_modes[settings["keying_mode"]]

    # BUTTON STATE TRACKING ############################################
    # DIT BUTTON ############################
    if dit_val == True and dit_held == False:
        dit_hold_start_time = current_time
        dit_held = True
    elif dit_val == False and dit_held == True:
        dit_held = False
        dit_release_time = current_time

    # DAH BUTTON ############################
    if dah_val == True and dah_held == False:
        dah_hold_start_time = current_time
        dah_held = True
    elif dah_val == False and dah_held == True:
        dah_held = False
        dah_release_time = current_time

    # IAMBIC A ##############################
    if keying_mode == 'Iambic A':
        if dit_val and dah_val:
            if last_d == 'dah':
                do_a_dit()
                last_d = 'dit'
            else:
                do_a_dah()
                last_d = 'dah'
        elif dit_val:
            do_a_dit()
            last_d = 'dit'
        elif dah_val:
            do_a_dah()
            last_d = 'dah'

    # IAMBIC B ##############################
    elif keying_mode == 'Iambic B':
        if dit_val and dah_val:
            bth_hld = True
            if last_d == 'dah':
                do_a_dit()
                last_d = 'dit'
            else:
                do_a_dah()
                last_d = 'dah'

        elif bth_hld_prev == True:
            if last_d == 'dah':
                do_a_dit()
                last_d = 'dit'
            else:
                do_a_dah()
                last_d = 'dah'

        elif dit_val:
            do_a_dit()
            last_d = 'dit'
        elif dah_val:
            do_a_dah()
            last_d = 'dah'

        bth_hld_prev = bth_hld
        bth_hld = False

    # ULTIMATIC #############################
    elif keying_mode == 'Ultimatic':
        if dit_val and dah_val:
            if dit_hold_start_time < dah_hold_start_time:
                do_a_dah()
            elif dit_hold_start_time > dah_hold_start_time:
                do_a_dit()
        elif dit_val:
            do_a_dit()
            last_d = 'dit'
        elif dah_val:
            do_a_dah()
            last_d = 'dah'

    # STRAIGHT KEY ##########################
    elif keying_mode == 'Straight Key':
        if dit_val or dah_val:
            buz.duty_u16(buz_volume)
            led.value(settings["led"])
        else:
            buz.duty_u16(0)
            led.value(0)

# Core engine update (handles keying + decoding timing)
def core_engine_update(dit_val, dah_val, current_time):
    keying_handler(dit_val, dah_val, current_time)
    gap_checker()

# MODE HANDLERS <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
# SANDBOX MODE ############################################
def sandbox_mode(dit_val, dah_val, current_time):
    core_engine_update(dit_val, dah_val, current_time)
    draw_sandbox_mode(morse_oled_content)

# TRAINING MODE ###########################################
def training_mode(dit_val, dah_val, current_time):
    core_engine_update(dit_val, dah_val, current_time)
    # Future: scoring / prompt logic
    draw_sandbox_mode(morse_oled_content)

# KEYBOARD REPLAY MODE ####################################
def keyboard_replay_mode(dit_val, dah_val, current_time):
    global keypad_last_output_print_time_ms, keypad_output_text, morse_oled_content, decoded_text
    core_engine_update(dit_val, dah_val, current_time)

    pressed_keys = keypad_device.read_keypad()

    if pressed_keys:
        keypad_handle_pressed_keys(pressed_keys)
    else:
        keypad_idle_time_checker()

    # Reset keys that are no longer pressed
    for key in keypad_button_previous_states:
        if not pressed_keys or key not in pressed_keys:
            keypad_button_previous_states[key] = False

    # # Periodic print
    # if ticks_diff(current_time, keypad_last_output_print_time_ms) >= keypad_output_print_interval_ms:
    #     print(keypad_output_text)
    #     keypad_last_output_print_time_ms = current_time

    # Encode the keypad letters to Morse
    morse_oled_content = ''
    decoded_text = ''
    morse_from_keypad = morse_encoder()  # converts keypad_output_text → morse
    draw_keyboard_replay_mode(keypad_output_text, morse_from_keypad)

# TELEGRAPH MODE ##########################################
def telegraph_mode(dit_val, dah_val, current_time):
    core_engine_update(dit_val, dah_val, current_time)
    oled.fill(0)
    oled.text("Telegraph Mode", 0, 0)
    draw_right_aligned(morse_oled_content[-max_characters:], 128, 16)
    oled.show()

# DEBUG MODE ##############################################
def debug_mode(dit_val, dah_val):
    oled.fill(0)
    oled.text("DEBUG MODE", 0, 0)
    oled.text("DIT: {}".format(dit_val), 0, 12)
    oled.text("DAH: {}".format(dah_val), 0, 22)
    oled.text("WPM: {}".format(settings["wpm"]), 0, 32)
    oled.show()

# <><><><><><><><><><><><><><><><><><><><><><>
# DATABASES & DICTIONARIES
# <><><><><><><><><><><><><><><><><><><><><><>
morse_alph_dictionary = {
    # Info sourced from https://en.wikipedia.org/wiki/Morse_code
    # Alphabet
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E",
    "..-.": "F", "--.": "G", "....": "H", "..": "I", ".---": "J",
    "-.-": "K", ".-..": "L", "--": "M", "-.": "N", "---": "O",
    ".--.": "P", "--.-": "Q", ".-.": "R", "...": "S", "-": "T",
    "..-": "U", "...-": "V", ".--": "W", "-..-": "X", "-.--": "Y",
    "--..": "Z",

    # Numbers
    "-----": "0", ".----": "1", "..---": "2", "...--": "3",
    "....-": "4", ".....": "5", "-....": "6", "--...": "7",
    "---..": "8", "----.": "9",

    # Punctuation (Does not include anything that collides with other characters)
    ".-.-.-": ".",      # Period
    "--..--": ",",      # Comma
    "..--..": "?",      # Question mark
    ".----.": "'",      # Apostrophe
    "-..-.": "/",       # Slash
    "-.--.": "(",       # Open parenthesis
    "-.--.-": ")",      # Close parenthesis
    "---...": ":",      # Colon
    "-.-.-.": ";",      # Semicolon
    "-...-": "=",       # Equals
    ".-.-.": "+",       # Plus
    "-....-": "-",      # Hyphen
    ".-..-.": "\"",     # Quotation mark
    ".--.-.": "@",      # At sign
    "-.-.--": "!",      # Exclamation
    "..--.-": "_",      # Underscore
    "...-..-": "$",     # Dollar
}

alph_morse_dictionary = {}  # Initialize
for morse_code in morse_alph_dictionary:         # Iterate over all keys in the original dict
    letter = morse_alph_dictionary[morse_code]   # Get the corresponding letter
    alph_morse_dictionary[letter] = morse_code   # Map letter --> morse code

# MODE TABLE
mode_handlers = {
    0: sandbox_mode,
    1: training_mode,
    2: keyboard_replay_mode,
    3: telegraph_mode,
    4: debug_mode,
}

# <><><><><><><><><><><><><><><><><><><><><><>
# INITIALIZATION
# <><><><><><><><><><><><><><><><><><><><><><>
# Clear Screen
oled.fill(0)

# Keying Mode Setup
modes = ['Sandbox', 'Training', 'Keyboard Replay', 'Telegraph', 'Debug']
keying_modes = ['Iambic A', 'Iambic B', 'Ultimatic', 'Straight Key']

# Button Status Tracking
bth_hld = False
bth_hld_prev = False
dit_held = False
dah_held = False
# Character Status Tracking
letter_space_happened = False
word_space_happened = False
last_d = 'dit'

# Stopwatches & Timer Tracking
dit_hold_start_time = 0
dah_hold_start_time = 0
dit_release_time = 0
dah_release_time = 0
last_morse_end_time = 0
idle_start_time = 0

# <><><><><><><><><><><><><><><><><><><><><><>
# MAIN LOOP
# <><><><><><><><><><><><><><><><><><><><><><>
while True:
    # REFRESH ON LOOP START ############################################
    dit_val = dit_in.value() == 0 # Set dit_val to True if the DIT paddle is currently pressed.
    dah_val = dah_in.value() == 0
    current_time = ticks_ms()

    # Dynamic Settings #################
    # Volume
    buz_volume = buz_vol_list[settings["volume"]]  # (volume 0-10), corisponds to the pwm in the volume list.
    # Timing
    dit_t = 1.2 / settings["wpm"] # dit_t matched WPM calculations
    dah_t = dit_t * 3  # Dah time length
    gap_t = dit_t  # Time between character sounding
    letter_break_t = dit_t * 3  # How long to wait until it is considered a new character.
    word_break_t = dit_t * 7  # How long to wait until it is considered a new word.

    # Menu Handling #################
    # Continue business as normal if the settings menu isn't open.
    if not settings_menu_open:
        current_mode = settings["mode"]
        mode_handlers[current_mode](dit_val, dah_val, current_time)

    # ROTARY SWITCH HANDLING (open menu immediately on hold)
    rotary_encoder_hold_threshhold = 2000  # milliseconds
    if sw.value() == 0:  # Button pressed
        if rotary_hold_start == 0:
            rotary_hold_start = current_time
            press_handled = False
        elif not press_handled and ticks_diff(current_time, rotary_hold_start) >= rotary_encoder_hold_threshhold:
            # Long hold triggers menu toggle
            settings_menu_open = not settings_menu_open  # open if closed, close if open
            if settings_menu_open:
                settings_menu_current_menu_mode = settings_menu_in_scrollable_menu
            else:
                settings_menu_current_menu_mode = settings_menu_open
            # Reset menu when opening
            if settings_menu_open:
                settings_menu_selected = 1 # First item in the list that's not a heading
                settings_menu_scroll = 0
            settings_menu_draw_menu()
            press_handled = True  # prevent multiple triggers

    elif sw.value() == 1 and rotary_hold_start != 0:  # Button released
        if not press_handled:
            # Short press toggles edit mode
            if settings_menu_open:
                if settings_menu_current_menu_mode == settings_menu_in_scrollable_menu:
                    settings_menu_current_menu_mode = settings_menu_in_editing_menu
                else:
                    settings_menu_current_menu_mode = settings_menu_in_scrollable_menu
                settings_menu_draw_menu()
        # Reset press tracking
        rotary_hold_start = 0
        press_handled = False

    # ROTARY ENCODER ROTATION
    current_clk = clk.value()
    current_dt = dt.value()
    if last_clk != current_clk:  # detect any edge
        if current_clk == 1:  # rising edge
            if current_dt == 0:
                delta = 1
            else:
                delta = -1
            rotary_encoder_handler(delta)
            if settings_menu_open:
                settings_menu_draw_menu() # Scroll happened, draw the menu.
    last_clk = current_clk