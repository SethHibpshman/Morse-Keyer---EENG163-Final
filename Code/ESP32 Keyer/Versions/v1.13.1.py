"""
Morse Keyer & Trainer — ESP32-S3
=================================
A MicroPython-based morse code keyer and trainer. Handles paddle input,
buzzer output, OLED display, rotary encoder settings menu, and a
multi-tap keypad for text-to-morse keyboard replay mode.

Hardware:
    - ESP32-S3 microcontroller (MicroPython)
    - SSD1306 128x64 OLED via SoftI2C
    - Buzzer on Pin 38
    - Dit paddle on Pin 7, Dah paddle on Pin 16
    - 4x4 matrix keypad on Pins 5,6,15,17 (rows) and 18,2,39,40 (cols)
    - Rotary encoder: CLK=4, DT=47, SW=45
    - External LED on Pin 1

Author: Seth Hibpshman
Course: EENG 163 Final Project
License: GNU GPL v3
"""

from machine import Pin, SoftI2C, PWM, reset
from keypad import Keypad
import ssd1306
import gfx
from time import sleep, ticks_ms, ticks_diff
import gc
import urandom

# <><><><><><><><><><><><><><><><><><><><><><>
# SETUP
# <><><><><><><><><><><><><><><><><><><><><><>

# HARDWARE ##############################

# Buzzer
buz = PWM(Pin(38))
buz.freq(700)
buz.duty_u16(0)
buz_vol_list = [0, 500, 1200, 2500, 5000, 9000, 15000, 23000, 33000, 46000, 58000]

# Paddles
dit_in = Pin(7,  Pin.IN, Pin.PULL_UP)
dah_in = Pin(16, Pin.IN, Pin.PULL_UP)

# Keypad hardware
keypad_gpio_row_pins    = [Pin(5), Pin(6), Pin(15), Pin(17)]
keypad_gpio_column_pins = [Pin(18), Pin(2), Pin(39), Pin(40)]
keypad_layout_keys = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']]
keypad_device = Keypad(keypad_gpio_row_pins, keypad_gpio_column_pins, keypad_layout_keys)

# Keypad software — press counters (one entry per key, initialised to 0)
keypad_button_press_counters = {}
for keypad_row in keypad_layout_keys:
    for keypad_key in keypad_row:
        keypad_button_press_counters[keypad_key] = 0

# Keypad software — previous state tracker (False = not pressed)
keypad_button_previous_states = {}
for keypad_row in keypad_layout_keys:
    for keypad_key in keypad_row:
        keypad_button_previous_states[keypad_key] = False

# Keypad multi-tap letter map (phone-style T9 layout)
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

# Keypad state tracking
keypad_idle_start_time_ms       = 0
keypad_idle_elapsed_time_ms     = 0
keypad_active_key               = None
keypad_tap_count                = 0
keypad_last_press_time_ms       = 0
keypad_multi_tap_timeout_ms     = 1000
keypad_output_text              = ""
keypad_control_keys             = {'*', '#', 'A', 'B', 'C', 'D', '1'}
keypad_output_print_interval_ms = 1000
keypad_last_output_print_time_ms = 0

# Rotary Encoder
clk = Pin(4,  Pin.IN, Pin.PULL_UP)
dt  = Pin(47, Pin.IN, Pin.PULL_UP)
sw  = Pin(45, Pin.IN, Pin.PULL_UP)
last_clk          = clk.value()
rotary_hold_start = 0       # Measures how long the rotary encoder button is held
settings_menu_open = False  # Tracks if settings menu is open — starts closed

# External LED
led = Pin(1, Pin.OUT)

# SSD1306 OLED
i2c      = SoftI2C(scl=Pin(46), sda=Pin(8))
oled     = ssd1306.SSD1306_I2C(128, 64, i2c)
oled_gfx = gfx.GFX(128, 64, oled.pixel)

# SETTINGS MENU ##############################
settings_menu_items = [
    # Tuples of (display label, key). Headings skip selection and editing.
    ("MODAL CONFIG",  "heading"),
    ("Mode",          "mode"),
    ("BEHAVIOR",      "heading"),
    ("Keying Mode",   "keying_mode"),
    ("Volume",        "volume"),
    ("LED",           "led"),
    ("Decoding",      "decoding"),
    ("OTHER",         "heading"),
    ("About",         "about"),
    ("Reset",         "reset"),
]

settings = {
    # Default values for each editable setting
    "wpm":         10,
    "mode":         4,
    "volume":       5,
    "led":       True,
    "keying_mode":  0,
    "decoding":  True,
}

settings_menu_selected           = 0   # Currently highlighted menu item index
settings_menu_scroll             = 0   # Top-most visible menu item index (for scrolling)
settings_menu_line_height        = 10  # Pixels per menu row
settings_menu_max_visible_lines  = 6   # How many rows fit on screen at once
settings_menu_in_scrollable_menu = 0   # Mode constant: browsing the menu
settings_menu_in_editing_menu    = 1   # Mode constant: editing a value
settings_menu_current_menu_mode  = settings_menu_in_scrollable_menu  # Start in scroll mode

about_scroll_offset = 0   # Current scroll position in the about screen (pixels)
about_scroll_speed  = 8   # Pixels scrolled per update call

# SOFTWARE ##############################

morse_oled_content = ''   # Accumulates all keyed morse symbols for display and decoding
decoded_text       = ''   # Human-readable decoded output built from morse_oled_content
max_characters     = 16   # Max chars shown on OLED per row (SSD1306 is 16 chars wide at 8px)

# Sleep
sleep_enabled    = True         # Can be toggled in settings
device_sleeping  = False        # Tracks current sleep state
sleep_timeout_ms = 60000        # Idle milliseconds before sleeping (60 seconds)
last_input_time  = ticks_ms()   # Timestamp of last user activity

# <><><><><><><><><><><><><><><><><><><><><><>
# FUNCTIONS
# <><><><><><><><><><><><><><><><><><><><><><>

def do_a_dit():
    """Sound a dit, append '.' to morse content, then observe inter-element gap."""
    global morse_oled_content, last_morse_end_time
    buz.duty_u16(buz_volume)
    led.value(settings["led"])
    morse_oled_content = morse_oled_content + '.'
    draw_sandbox_mode(morse_oled_content)
    sleep(dit_t)
    buz.duty_u16(0)
    led.value(0)
    sleep(gap_t)
    last_morse_end_time = ticks_ms()

def do_a_dah():
    """Sound a dah, append '-' to morse content, then observe inter-element gap."""
    global morse_oled_content, last_morse_end_time
    buz.duty_u16(buz_volume)
    led.value(settings["led"])
    morse_oled_content = morse_oled_content + '-'
    draw_sandbox_mode(morse_oled_content)
    sleep(dah_t)
    buz.duty_u16(0)
    led.value(0)
    sleep(gap_t)
    last_morse_end_time = ticks_ms()

def play_morse_string(morse_str):
    """
    Play back a pre-built morse string through the buzzer.

    Handles '.', '-', ' ' (letter break), and '/' (word break) symbols.
    Decodes and updates the display after each separator.

    Parameters
    ----------
    morse_str : str
        A morse string e.g. '... --- ...' to play back sequentially.

    Returns
    -------
    None
    """
    global morse_oled_content, decoded_text
    n = len(morse_str)
    for i, symbol in enumerate(morse_str):
        last_symbol = (i == n - 1)

        if symbol == '.':
            do_a_dit()
        elif symbol == '-':
            do_a_dah()
        elif symbol == ' ':
            # Letter break — decode the last letter and insert a space
            morse_decoder()
            morse_oled_content += ' '
            draw_sandbox_mode(morse_oled_content)
            sleep(letter_break_t)
        elif symbol == '/':
            # Word break — decode, insert slash, add decoded space
            morse_decoder()
            morse_oled_content += '/'
            decoded_text += ' '
            draw_sandbox_mode(morse_oled_content)
            sleep(word_break_t)

        # Treat the final symbol as a word break
        if last_symbol:
            morse_decoder()
            morse_oled_content += '/'
            decoded_text += ' '
            draw_sandbox_mode(morse_oled_content)
            sleep(word_break_t)

# DISPLAY HELPERS <><><><><><><><><><><><><><><><><><><><><><><><>

def draw_centered(text, center_x, y):
    """
    Draw text centred on a given x coordinate.

    Parameters
    ----------
    text : str
        String to render.
    center_x : int
        Pixel x position to centre the text around.
    y : int
        Pixel y position (top of text).
    """
    width = len(text) * 8
    x = center_x - (width // 2)
    oled.text(text, x, y)

def draw_right_aligned(text, right_x, y):
    """
    Draw text so its right edge sits at right_x.

    Parameters
    ----------
    text : str
        String to render.
    right_x : int
        Pixel x position of the right edge.
    y : int
        Pixel y position (top of text).
    """
    width = len(text) * 8  # 8 pixels per character
    x = right_x - width
    oled.text(text, x, y)

# MODE DRAW FUNCTIONS <><><><><><><><><><><><><><><><><><><><><><><><>

def draw_sandbox_mode(morse_oled_content=None):
    """
    Render the sandbox mode screen.

    Shows the last max_characters of morse content on row 1, and
    optionally the decoded text on row 2 if decoding is enabled.

    Parameters
    ----------
    morse_oled_content : str, optional
        Current morse string to display. Nothing is drawn if None.
    """
    oled.fill(0)
    if morse_oled_content is not None:
        oled.text('Morse:', 0, 0)
        draw_right_aligned((morse_oled_content[-max_characters:]), 128, 12)
        if settings["decoding"] == True:
            draw_right_aligned((decoded_text[-max_characters:]), 128, 24)
    oled.show()

def draw_keyboard_replay_mode(keypad_text, morse_text):
    """
    Render the keyboard replay mode screen.

    Shows the live morse string on row 1 and the alphabetic
    keypad input string on rows 2–3.

    Parameters
    ----------
    keypad_text : str
        The current alphabetic string built from keypad multi-tap input.
    morse_text : str
        The morse encoding of keypad_text to display.
    """
    oled.fill(0)
    oled.text('Morse:', 0, 0)
    draw_right_aligned(morse_text[-max_characters:], 128, 12)
    oled.text('Alph. Input:', 0, 24)
    oled.text(keypad_text[-max_characters:], 0, 36)
    oled.show()

# SETTINGS MENU <><><><><><><><><><><><><><><><><><><><><><><><>

def settings_menu_draw_menu():
    """
    Render the settings menu in either scrollable or editing mode.

    Scrollable mode shows a highlighted list of menu items.
    Editing mode shows the selected item's current value and allows changes.
    Headings are underlined and cannot be selected.
    """
    oled.fill(0)
    global settings_menu_scroll

    # EDITING MENU ########################
    if settings_menu_current_menu_mode == settings_menu_in_editing_menu:
        item  = settings_menu_items[settings_menu_selected]
        label = item[0]
        key   = item[1]

        if key not in ["heading", "about", "reset"]:
            value_of_currently_selected_menu_item = value_to_str(key, settings[key])
            draw_centered(label, 64, 18)
            draw_centered(value_of_currently_selected_menu_item, 64, 36)
        elif key == "about":
            draw_about_screen()
        elif key == "reset":
            device_reset()
        oled.show()
        return

    # SCROLLABLE SETTINGS MAIN MENU ########################
    # Keep heading visible when the first item beneath it is selected
    extra_heading_line = 0
    if settings_menu_selected == 1:
        extra_heading_line = 1

    if settings_menu_selected < settings_menu_scroll + extra_heading_line:
        settings_menu_scroll = settings_menu_selected - extra_heading_line
    elif settings_menu_selected >= settings_menu_scroll + settings_menu_max_visible_lines:
        settings_menu_scroll = settings_menu_selected - settings_menu_max_visible_lines + 1

    # Render only the visible window of items
    for i in range(settings_menu_scroll, min(settings_menu_scroll + settings_menu_max_visible_lines, len(settings_menu_items))):
        pixel_y = (i - settings_menu_scroll) * settings_menu_line_height
        if pixel_y + settings_menu_line_height > 64:
            continue  # Never clip past the bottom of the screen

        item  = settings_menu_items[i]
        label = item[0]
        key   = item[1]

        if key == "heading":
            oled.text(label, 4, pixel_y + 1, 1)
            oled_gfx.fill_rect(4, pixel_y + 9, len(label) * 8, 1, 1)  # Underline
        else:
            if i == settings_menu_selected:
                # Highlight selected item: white bar, black text
                oled_gfx.fill_rect(0, pixel_y + 1, 128, settings_menu_line_height - 2, 1)
                oled.text(label, 12, pixel_y + 1, 0)
            else:
                oled.text(label, 12, pixel_y + 1, 1)
    oled.show()

def draw_about_screen():
    """
    Render the scrolling about/credits screen.

    Scrolls upward on each call by about_scroll_speed pixels.
    Loops back to the start when the end of the credits is reached.
    """
    global about_scroll_offset
    oled.fill(0)
    credits = [
        "Scroll!",
        "", "", "",
        "Morse Keyer &",
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
        "", "", "",
        "The End <3 :)",
    ]

    total_height = len(credits) * 8
    y_start = 64 - 8 - about_scroll_offset  # Begin one line above the bottom edge

    for line_number, line_content in enumerate(credits):
        y = y_start + line_number * 8
        if -8 < y < 64:  # Only draw lines that are actually on screen
            oled.text(line_content, 0, y, 1)

    oled.show()
    about_scroll_offset += about_scroll_speed

    # Loop back to the beginning once all credits have scrolled past
    if about_scroll_offset > total_height + 64:
        about_scroll_offset = 0

# MORSE ENGINE <><><><><><><><><><><><><><><><><><><><><><><><>

def morse_decoder():
    """
    Decode the last morse letter in morse_oled_content and append it to decoded_text.

    Finds the most recent '/' or ' ' separator, extracts the symbol after it,
    and looks it up in morse_alph_dictionary. Appends '?' for unknown sequences.
    """
    global decoded_text
    index_last_slash = morse_oled_content.rfind('/')
    index_last_space = morse_oled_content.rfind(' ')
    last_break_index = max(index_last_slash, index_last_space)

    last_morse_letter = morse_oled_content[last_break_index + 1:].strip()

    if last_morse_letter:
        if morse_alph_dictionary.get(last_morse_letter):
            decoded_text = decoded_text + morse_alph_dictionary[last_morse_letter]
        else:
            decoded_text = decoded_text + '?'  # Unknown sequence

def morse_encoder():
    """
    Encode keypad_output_text into a morse string.

    Spaces become '/' word separators. Each letter is looked up in
    alph_morse_dictionary and separated by a space. Unknown characters
    are replaced with '?'.

    Returns
    -------
    str
        Morse string e.g. '... --- ...' representing keypad_output_text.
    """
    morse_out = ''
    for ch in keypad_output_text:
        if ch == ' ':
            morse_out = morse_out + '/'  # Word separator
        else:
            morse_out = morse_out + alph_morse_dictionary.get(ch, '?') + ' '
    return morse_out.strip()

def gap_checker():
    """
    Detect letter and word gaps between paddle presses and insert separators.

    Monitors idle time since the last paddle activity. If idle exceeds
    letter_break_t a space is inserted; if it further exceeds word_break_t
    the space is upgraded to a '/'.
    """
    global morse_oled_content, idle_start_time, letter_space_happened, word_space_happened, decoded_text

    if dit_val == False and dah_val == False:
        # No paddle activity — start or continue counting idle time
        if idle_start_time == 0:
            idle_start_time = current_time
        idle_time = ticks_diff(current_time, idle_start_time)

        # Insert letter space after letter_break_t milliseconds
        if idle_time >= int(letter_break_t * 1000) and letter_space_happened == False:
            morse_decoder()
            morse_oled_content = morse_oled_content + ' '
            draw_sandbox_mode(morse_oled_content)
            letter_space_happened = True
            word_space_happened   = False

        # Upgrade letter space to word break after word_break_t milliseconds
        if letter_space_happened == True and word_space_happened == False:
            if idle_time >= int((word_break_t) * 1000):
                if morse_oled_content and morse_oled_content[-1] == ' ':
                    morse_oled_content = morse_oled_content[:-1] + '/'
                    decoded_text = decoded_text + ' '
                draw_sandbox_mode(morse_oled_content)
                word_space_happened = True
    else:
        # Paddle active — reset all gap tracking
        idle_start_time       = 0
        letter_space_happened = False
        word_space_happened   = False

def keying_handler(dit_val, dah_val, current_time):
    """
    Dispatch paddle presses to the correct keying mode logic.

    Supported modes: Iambic A, Iambic B, Ultimatic, Straight Key.
    Also tracks hold start times and release times for each paddle.

    Parameters
    ----------
    dit_val : bool
        True if the dit paddle is currently pressed.
    dah_val : bool
        True if the dah paddle is currently pressed.
    current_time : int
        Current ticks_ms() value.
    """
    global last_d
    global bth_hld, bth_hld_prev
    global dit_hold_start_time, dah_hold_start_time
    global dit_held, dah_held
    global dit_release_time, dah_release_time

    keying_mode = keying_modes[settings["keying_mode"]]

    # BUTTON STATE TRACKING ############################################
    if dit_val == True and dit_held == False:
        dit_hold_start_time = current_time
        dit_held = True
    elif dit_val == False and dit_held == True:
        dit_held = False
        dit_release_time = current_time

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
                do_a_dit(); last_d = 'dit'
            else:
                do_a_dah(); last_d = 'dah'
        elif dit_val:
            do_a_dit(); last_d = 'dit'
        elif dah_val:
            do_a_dah(); last_d = 'dah'

    # IAMBIC B ##############################
    elif keying_mode == 'Iambic B':
        if dit_val and dah_val:
            bth_hld = True
            if last_d == 'dah':
                do_a_dit(); last_d = 'dit'
            else:
                do_a_dah(); last_d = 'dah'
        elif bth_hld_prev == True:
            if last_d == 'dah':
                do_a_dit(); last_d = 'dit'
            else:
                do_a_dah(); last_d = 'dah'
        elif dit_val:
            do_a_dit(); last_d = 'dit'
        elif dah_val:
            do_a_dah(); last_d = 'dah'

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
            do_a_dit(); last_d = 'dit'
        elif dah_val:
            do_a_dah(); last_d = 'dah'

    # STRAIGHT KEY ##########################
    elif keying_mode == 'Straight Key':
        if dit_val or dah_val:
            buz.duty_u16(buz_volume)
            led.value(settings["led"])
        else:
            buz.duty_u16(0)
            led.value(0)

def core_engine_update(dit_val, dah_val, current_time):
    """
    Run one tick of the morse engine: keying then gap detection.

    Parameters
    ----------
    dit_val : bool
        True if the dit paddle is currently pressed.
    dah_val : bool
        True if the dah paddle is currently pressed.
    current_time : int
        Current ticks_ms() value.
    """
    keying_handler(dit_val, dah_val, current_time)
    gap_checker()

# KEYPAD FUNCTIONS <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>

def keypad_handle_pressed_keys(pressed_keys):
    """
    Process a list of currently pressed keypad keys.

    Handles edge detection so each physical press fires once. Routes
    control keys immediately and applies multi-tap logic to letter keys.

    Parameters
    ----------
    pressed_keys : list[str]
        Keys currently reported as pressed by keypad_device.read_keypad().
    """
    global keypad_active_key, keypad_tap_count, keypad_last_press_time_ms
    global current_time, keypad_idle_start_time_ms

    keypad_current_key = pressed_keys[0]  # Only process one key at a time
    keypad_idle_start_time_ms = 0         # Reset idle timer on any key press

    # Edge detection — only act on a new press
    if not keypad_button_previous_states[keypad_current_key]:

        # CONTROL KEY BLOCK (no multi-tap) #######
        if keypad_current_key in keypad_control_keys:
            keypad_commit_active_key()
            keypad_handle_control_key(keypad_current_key)
            keypad_button_previous_states[keypad_current_key] = True
            return

        # MULTI-TAP LETTER KEYS ##################
        if (keypad_current_key == keypad_active_key and
                ticks_diff(current_time, keypad_last_press_time_ms) < keypad_multi_tap_timeout_ms):
            keypad_tap_count = keypad_tap_count + 1
            keypad_overwrite_last_character()
        else:
            # First press of a new key — commit any pending letter first
            keypad_commit_active_key()
            keypad_active_key = keypad_current_key
            keypad_tap_count  = 1
            keypad_append_new_character()

        keypad_last_press_time_ms = current_time
        keypad_button_previous_states[keypad_current_key] = True

def keypad_idle_time_checker():
    """
    Commit the active multi-tap key if the tap timeout has elapsed.

    Should be called every loop tick when no keys are pressed so that
    the last tapped letter is finalised after the user stops tapping.
    """
    global keypad_idle_start_time_ms, current_time, keypad_idle_elapsed_time_ms, keypad_active_key

    if keypad_active_key is None:
        return  # Nothing pending

    if keypad_idle_start_time_ms == 0:
        keypad_idle_start_time_ms = current_time

    keypad_idle_elapsed_time_ms = ticks_diff(current_time, keypad_idle_start_time_ms)

    if keypad_idle_elapsed_time_ms >= keypad_multi_tap_timeout_ms:
        keypad_commit_active_key()
        keypad_idle_start_time_ms = 0

def keypad_commit_active_key():
    """Finalise the current multi-tap sequence and clear the active key state."""
    global keypad_active_key, keypad_tap_count
    if keypad_active_key is None:
        return
    keypad_active_key = None
    keypad_tap_count  = 0

def keypad_append_new_character():
    """Append the letter for the current active key and tap count to keypad_output_text."""
    global keypad_output_text
    if keypad_active_key is None:
        return
    letter = keypad_get_letter_for_keypad_key(keypad_active_key, keypad_tap_count)
    keypad_output_text = keypad_output_text + letter

def keypad_overwrite_last_character():
    """Replace the last character in keypad_output_text with the current multi-tap letter."""
    global keypad_output_text
    if len(keypad_output_text) == 0 or keypad_active_key is None:
        return
    letter = keypad_get_letter_for_keypad_key(keypad_active_key, keypad_tap_count)
    keypad_output_text = keypad_output_text[:-1] + letter

def keypad_get_letter_for_keypad_key(key, tap_count):
    """
    Return the letter corresponding to a key and tap count.

    Wraps around the letter list if tap_count exceeds the number of
    letters mapped to that key (e.g. tapping '7' five times → 'P').

    Parameters
    ----------
    key : str
        The keypad key character (e.g. '2', '7').
    tap_count : int
        How many times the key has been tapped in this sequence.

    Returns
    -------
    str
        The resolved single character for this tap.
    """
    if key in keypad_multi_tap_letter_map:
        letters = keypad_multi_tap_letter_map[key]
        index   = (tap_count - 1) % len(letters)
        return letters[index]
    else:
        return key  # Keys not in the map return themselves

def keypad_handle_control_key(key):
    """
    Execute the action bound to a control key press.

    Control keys perform immediate actions rather than entering letters.
    'A' is backspace, 'B' encodes and plays the current keypad text as morse.
    All other control keys are stubs for future use.

    Parameters
    ----------
    key : str
        The control key pressed (one of keypad_control_keys).
    """
    global keypad_output_text

    if key == '*':
        print("Pressed: *")

    elif key == '#':
        print("Pressed: #")

    elif key == 'A':
        # Backspace — remove the last character
        if len(keypad_output_text) > 0:
            keypad_output_text = keypad_output_text[:-1]
            print(keypad_output_text)

    elif key == 'B':
        # Play the current keypad text as morse
        morse_str = morse_encoder()
        play_morse_string(morse_str)

    elif key == 'C':
        print("Pressed: C")

    elif key == 'D':
        print("Pressed: D")

    elif key == '1':
        print("Pressed: 1")

# SETTINGS HELPERS <><><><><><><><><><><><><><><><><><><><><><><><>

def value_to_str(key, menu_value):
    """
    Convert a settings value to a human-readable string for the editing menu.

    Parameters
    ----------
    key : str
        The settings dictionary key (e.g. 'mode', 'volume').
    menu_value : any
        The current value stored for that key.

    Returns
    -------
    str
        Display string for the editing menu (e.g. 'Enabled', 'Sandbox').
    """
    if key == "mode":
        return modes[menu_value]
    if key == "keying_mode":
        return keying_modes[menu_value]
    if key in ["led", "decoding"]:
        return "Enabled" if menu_value else "Disabled"
    return str(menu_value)

def rotary_encoder_handler(delta):
    """
    Handle rotary encoder rotation in both scrollable and editing menu modes.

    In scrollable mode, moves the selection cursor while skipping headings.
    In editing mode, increments or decrements the selected setting's value.

    Parameters
    ----------
    delta : int
        +1 for clockwise rotation, -1 for counter-clockwise.
    """
    global settings_menu_selected

    # SCROLLABLE SETTINGS MAIN MENU ########################
    if settings_menu_current_menu_mode == settings_menu_in_scrollable_menu:
        next_index = settings_menu_selected
        while True:
            next_index = (next_index + delta) % len(settings_menu_items)
            key = settings_menu_items[next_index][1]
            if key not in ["heading"]:  # Skip headings, allow action items
                break
        settings_menu_selected = next_index

    # EDITING MENU ##########################################
    elif settings_menu_current_menu_mode == settings_menu_in_editing_menu:
        item = settings_menu_items[settings_menu_selected]
        key  = item[1]

        if key not in ["mode", "keying_mode", "volume", "led", "decoding", "wpm"]:
            return  # Non-editable item — do nothing

        menu_value = settings[key]
        if key == "wpm":
            settings[key] = min(max(10, menu_value + delta), 40)   # Clamp 10–40
        elif key == "volume":
            settings[key] = min(max(0,  menu_value + delta), 10)   # Clamp 0–10
        elif key in ["led", "decoding"]:
            if delta != 0:
                settings[key] = not menu_value                      # Toggle bool
        elif key == "mode":
            settings[key] = (menu_value + delta) % len(modes)
        elif key == "keying_mode":
            settings[key] = (menu_value + delta) % len(keying_modes)

# MODE HANDLERS <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>

def sandbox_mode(dit_val, dah_val, current_time):
    """Run the engine and refresh the sandbox display."""
    core_engine_update(dit_val, dah_val, current_time)
    draw_sandbox_mode(morse_oled_content)

def training_mode(dit_val, dah_val, current_time):
    """Run the engine and refresh the training display. (Scoring TBD)"""
    core_engine_update(dit_val, dah_val, current_time)
    draw_sandbox_mode(morse_oled_content)

def keyboard_replay_mode(dit_val, dah_val, current_time):
    """
    Handle keypad text entry and live morse preview.

    Reads the keypad each tick, processes multi-tap input, then encodes
    the current keypad text to morse and redraws the display. Paddle
    input is still active so the user can manually key alongside.

    Parameters
    ----------
    dit_val : bool
        True if the dit paddle is currently pressed.
    dah_val : bool
        True if the dah paddle is currently pressed.
    current_time : int
        Current ticks_ms() value.
    """
    global keypad_last_output_print_time_ms, keypad_output_text
    global morse_oled_content, decoded_text

    core_engine_update(dit_val, dah_val, current_time)

    pressed_keys = keypad_device.read_keypad()

    if pressed_keys:
        keypad_handle_pressed_keys(pressed_keys)
    else:
        keypad_idle_time_checker()

    # Reset keys that are no longer held
    for key in keypad_button_previous_states:
        if not pressed_keys or key not in pressed_keys:
            keypad_button_previous_states[key] = False

    # Encode live keypad text to morse and refresh display
    morse_oled_content = ''
    decoded_text       = ''
    morse_from_keypad  = morse_encoder()
    draw_keyboard_replay_mode(keypad_output_text, morse_from_keypad)

def debug_mode(dit_val, dah_val, current_time):
    """
    Display live diagnostic information — paddle state, encoder pins, keypad, memory, clock.

    Parameters
    ----------
    dit_val : bool
        Current dit paddle state.
    dah_val : bool
        Current dah paddle state.
    current_time : int
        Current ticks_ms() value.
    """
    oled.fill(0)

    heading = 'DEBUG MODE:'
    oled.text(f"{heading}", 0, 0)
    oled_gfx.fill_rect(4, 9, len(heading) * 8, 1, 1)  # Underline

    dit_state = "ON" if dit_val else "OFF"
    dah_state = "ON" if dah_val else "OFF"
    oled.text(f"DIT/DAH: {dit_state}/{dah_state}", 0, 12)
    oled.text(f"ENC C:{clk.value()} D:{dt.value()} S:{sw.value()}", 0, 22)

    pressed_keys = keypad_device.read_keypad()
    oled.text("KEYPAD:", 0, 32)
    if pressed_keys:
        oled.text(pressed_keys, 60, 32)
    else:
        oled.text("-", 60, 32)

    free = gc.mem_free()
    used = gc.mem_alloc()
    oled.text(f"F:{free // 1024:03d}kB", 0, 44)
    oled.text(f"U:{used // 1024:03d}kB", 64, 44)
    oled.text(f"CLK: {current_time} ms", 0, 56)
    oled.show()

# DEVICE CONTROL <><><><><><><><><><><><><><><><><><><><><><><><>

def device_reset():
    """Show an animated reset countdown on the OLED then hard-reset the device."""
    for i in range(0, 4):
        oled.fill(0)
        draw_centered("Resetting" + "." * i, 64, 28)
        oled.show()
        sleep(0.5)
    reset()

def sleep_device():
    """Blank the display, silence the buzzer, and mark the device as sleeping."""
    global device_sleeping
    device_sleeping = True
    oled.fill(0)
    oled.show()
    buz.duty_u16(0)
    led.value(0)

def wake_device():
    """Mark the device as awake and reset the idle timer."""
    global device_sleeping, last_input_time
    device_sleeping = False
    last_input_time = ticks_ms()

# SCREENSAVER <><><><><><><><><><><><><><><><><><><><><><><><>

def draw_bitmap(x, y, bitmap, width, height):
    """
    Draw a column-major 1-bit bitmap onto the OLED at (x, y).

    Parameters
    ----------
    x : int
        Left pixel coordinate.
    y : int
        Top pixel coordinate.
    bitmap : list[int]
        Raw bitmap bytes in column-major order (8 vertical pixels per byte).
    width : int
        Bitmap width in pixels.
    height : int
        Bitmap height in pixels.
    """
    # Clear the bounding box first
    for px in range(width):
        for py in range(height):
            oled.pixel(x + px, y + py, 0)

    bytes_per_col = (height + 7) // 8
    for col in range(width):
        for byte_index in range(bytes_per_col):
            byte = bitmap[col + byte_index * width]
            for bit in range(8):
                pixel_y = y + byte_index * 8 + bit
                if pixel_y >= y + height:
                    continue
                color = (byte >> bit) & 0x01
                oled.pixel(x + col, pixel_y, color)

def draw_bouncing_logo():
    """
    Animate the logo bitmap bouncing around the OLED screen (DVD screensaver style).

    Randomly flips the perpendicular velocity component on each wall bounce
    to vary the trajectory. Updates logo_x, logo_y, logo_dx, logo_dy globals.
    """
    global logo_x, logo_y, logo_dx, logo_dy

    logo_x += logo_dx
    logo_y += logo_dy

    # Horizontal bounds
    if logo_x <= 0:
        logo_x = 0
        logo_dx = abs(logo_dx)
        if urandom.getrandbits(1):
            logo_dy = -logo_dy
    elif logo_x + logo_width >= 128:
        logo_x = 128 - logo_width
        logo_dx = -abs(logo_dx)
        if urandom.getrandbits(1):
            logo_dy = -logo_dy

    # Vertical bounds
    if logo_y <= 0:
        logo_y = 0
        logo_dy = abs(logo_dy)
        if urandom.getrandbits(1):
            logo_dx = -logo_dx
    elif logo_y + logo_height >= 64:
        logo_y = 64 - logo_height
        logo_dy = -abs(logo_dy)
        if urandom.getrandbits(1):
            logo_dx = -logo_dx

    oled.fill(0)
    draw_bitmap(logo_x, logo_y, logo_bitmap, logo_width, logo_height)
    oled.show()

# BOOT SCREEN <><><><><><><><><><><><><><><><><><><><><><><><>

def draw_boot_screen():
    """
    Play a typewriter-style boot sequence on the OLED.

    Streams each character of each boot message with a blinking cursor,
    scrolling upward when the screen fills. Pauses briefly after each line,
    then holds for 2 seconds at the end before returning.
    """
    oled.fill(0)
    oled.show()

    cursor_w, cursor_h = 8, 8
    line_height        = 8
    max_chars_per_line = 128 // 8   # 16 characters
    max_visible_lines  = 64  // 8   # 8 rows

    messages = [
        "SETH INC. 2026",
        "ESP32-S3 V1.13",
        "Init Memory....." "OK",
        "Peripherals....." "OK",
        "Load Sys Fls...." "OK",
        "Self-Test......." "OK",
        "Boot Complete.",
        "_"
    ]

    # Word-wrap all messages to screen width
    wrapped_lines = []
    for msg in messages:
        while msg:
            wrapped_lines.append(msg[:max_chars_per_line])
            msg = msg[max_chars_per_line:]

    screen_lines = []

    for line in wrapped_lines:
        for char_index, char in enumerate(line):
            if char_index == 0:
                screen_lines.append("")
                if len(screen_lines) > max_visible_lines:
                    screen_lines.pop(0)  # Scroll oldest line off the top

            screen_lines[-1] += char

            oled.fill(0)
            for i, l in enumerate(screen_lines):
                oled.text(l, 0, i * line_height)

            # Draw blinking block cursor at end of current line
            cursor_x = len(screen_lines[-1]) * 8
            cursor_y = (len(screen_lines) - 1) * line_height
            oled_gfx.fill_rect(cursor_x, cursor_y, cursor_w, cursor_h, 1)
            oled.show()
            sleep(0.04)

            # Erase cursor before next character
            oled_gfx.fill_rect(cursor_x, cursor_y, cursor_w, cursor_h, 0)

        sleep(0.1)
    sleep(2)

# <><><><><><><><><><><><><><><><><><><><><><>
# DATABASES & DICTIONARIES
# <><><><><><><><><><><><><><><><><><><><><><>

# Morse → Letter  (source: https://en.wikipedia.org/wiki/Morse_code)
morse_alph_dictionary = {
    # Alphabet
    ".-": "A",   "-...": "B", "-.-.": "C", "-..": "D",  ".": "E",
    "..-.": "F", "--.": "G",  "....": "H", "..": "I",   ".---": "J",
    "-.-": "K",  ".-..": "L", "--": "M",   "-.": "N",   "---": "O",
    ".--.": "P", "--.-": "Q", ".-.": "R",  "...": "S",  "-": "T",
    "..-": "U",  "...-": "V", ".--": "W",  "-..-": "X", "-.--": "Y",
    "--..": "Z",
    # Numbers
    "-----": "0", ".----": "1", "..---": "2", "...--": "3",
    "....-": "4", ".....": "5", "-....": "6", "--...": "7",
    "---..": "8", "----.": "9",
    # Punctuation
    ".-.-.-": ".",  "--..--": ",",  "..--..": "?",  ".----.": "'",
    "-..-.":  "/",  "-.--.":  "(",  "-.--.-": ")",  "---...": ":",
    "-.-.-.": ";",  "-...-":  "=",  ".-.-.":  "+",  "-....-": "-",
    ".-..-.": "\"", ".--.-.": "@",  "-.-.--": "!",  "..--.-": "_",
    "...-..-": "$",
}

# Letter → Morse  (reverse of morse_alph_dictionary)
alph_morse_dictionary = {}
for morse_code in morse_alph_dictionary:
    letter = morse_alph_dictionary[morse_code]
    alph_morse_dictionary[letter] = morse_code

# Mode index → handler function
mode_handlers = {
    0: sandbox_mode,
    1: training_mode,
    2: keyboard_replay_mode,
    4: debug_mode,
}

# <><><><><><><><><><><><><><><><><><><><><><>
# INITIALIZATION
# <><><><><><><><><><><><><><><><><><><><><><>

oled.fill(0)

modes        = ['Sandbox', 'Training', 'Keyboard Replay', 'Telegraph', 'Debug']
keying_modes = ['Iambic A', 'Iambic B', 'Ultimatic', 'Straight Key']

# Button state tracking
bth_hld      = False
bth_hld_prev = False
dit_held     = False
dah_held     = False

# Character gap state tracking
letter_space_happened = False
word_space_happened   = False
last_d                = 'dit'

# Timers
dit_hold_start_time = 0
dah_hold_start_time = 0
dit_release_time    = 0
dah_release_time    = 0
last_morse_end_time = 0
idle_start_time     = 0

# Bouncing logo screensaver state
logo_x      = 0
logo_y      = 0
logo_dx     = 1   # Horizontal step (pixels per frame)
logo_dy     = 1   # Vertical step (pixels per frame)
logo_width  = 32
logo_height = 32
logo_bitmap = [
    0x80, 0xE0, 0xF8, 0x7C, 0x3E, 0x1E, 0x0F, 0x07, 0x07, 0x07, 0x07, 0x0F, 0x0E, 0x1E, 0x3E, 0x7C,
    0xFC, 0xE0, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0xF0, 0xFC, 0xFE, 0x0F, 0x07, 0x0F, 0xFE, 0xF8,
    0x03, 0x0F, 0x1F, 0x3E, 0x3C, 0x3C, 0x78, 0x78, 0xF0, 0xF0, 0xE0, 0xC0, 0x80, 0x80, 0x00, 0x00,
    0x01, 0x1F, 0xFF, 0xFE, 0xF0, 0x80, 0x00, 0x80, 0xCF, 0xFF, 0xFF, 0xF4, 0x78, 0x3C, 0x1F, 0x0F,
    0xC0, 0xF0, 0xF8, 0x38, 0x3C, 0x1C, 0x3C, 0x38, 0x78, 0xF1, 0xE1, 0x03, 0x0F, 0x1F, 0xFE, 0xFC,
    0xF8, 0x00, 0x01, 0xFF, 0xFF, 0xFF, 0x0F, 0x07, 0x03, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00,
    0x07, 0x1F, 0x3E, 0x7C, 0x70, 0xF0, 0xE3, 0xE7, 0xE6, 0xE7, 0xF3, 0x70, 0x78, 0x3C, 0x3F, 0x1F,
    0x07, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x03, 0x3F, 0xFF, 0xFE, 0xE0, 0x80, 0x00,
]

# <><><><><><><><><><><><><><><><><><><><><><>
# MAIN LOOP
# <><><><><><><><><><><><><><><><><><><><><><>

draw_boot_screen()

while True:
    # REFRESH ON LOOP START ############################################
    dit_val      = dit_in.value() == 0   # True when dit paddle is pressed
    dah_val      = dah_in.value() == 0
    current_time = ticks_ms()

    # Dynamic settings (recalculated each tick to reflect live changes)
    buz_volume     = buz_vol_list[settings["volume"]]
    dit_t          = 1.2 / settings["wpm"]  # Dit duration matched to WPM
    dah_t          = dit_t * 3              # Dah is 3x a dit
    gap_t          = dit_t                  # Inter-element gap
    letter_break_t = dit_t * 3             # Idle before new letter
    word_break_t   = dit_t * 7             # Idle before new word

    # MODE DISPATCH ############################################
    if not settings_menu_open and not device_sleeping:
        current_mode = settings["mode"]
        mode_handlers[current_mode](dit_val, dah_val, current_time)

    # ROTARY SWITCH HANDLING ############################################
    rotary_encoder_hold_threshold = 2000  # ms to trigger long-hold menu toggle
    if sw.value() == 0:
        if rotary_hold_start == 0:
            rotary_hold_start = current_time
            press_handled = False
        elif not press_handled and ticks_diff(current_time, rotary_hold_start) >= rotary_encoder_hold_threshold:
            # Long hold — toggle the settings menu open/closed
            settings_menu_open = not settings_menu_open
            if settings_menu_open:
                settings_menu_current_menu_mode = settings_menu_in_scrollable_menu
                settings_menu_selected = 1  # First non-heading item
                settings_menu_scroll   = 0
            else:
                settings_menu_current_menu_mode = settings_menu_open
            settings_menu_draw_menu()
            press_handled = True

    elif sw.value() == 1 and rotary_hold_start != 0:
        if not press_handled:
            # Short press — toggle between scroll and edit mode
            if settings_menu_open:
                if settings_menu_current_menu_mode == settings_menu_in_scrollable_menu:
                    settings_menu_current_menu_mode = settings_menu_in_editing_menu
                else:
                    settings_menu_current_menu_mode = settings_menu_in_scrollable_menu
                settings_menu_draw_menu()
        rotary_hold_start = 0
        press_handled     = False

    # ROTARY ENCODER ROTATION ############################################
    current_clk = clk.value()
    current_dt  = dt.value()
    if last_clk != current_clk:
        if current_clk == 1:  # Rising edge
            delta = 1 if current_dt == 0 else -1
            last_input_time = current_time
            if device_sleeping:
                wake_device()
            rotary_encoder_handler(delta)
            if settings_menu_open:
                settings_menu_draw_menu()
    last_clk = current_clk

    # SLEEP HANDLING ############################################
    if sleep_enabled and not device_sleeping:
        if ticks_diff(current_time, last_input_time) > sleep_timeout_ms:
            sleep_device()

    # ACTIVITY — reset idle timer on any paddle, keypad, or encoder press
    pressed_keys = keypad_device.read_keypad()
    if dit_val or dah_val or sw.value() == 0 or pressed_keys:
        last_input_time = current_time
        if device_sleeping:
            wake_device()

    # SCREENSAVER ############################################
    if sleep_enabled:
        if device_sleeping:
            draw_bouncing_logo()
            sleep(0.02)
        elif ticks_diff(current_time, last_input_time) > sleep_timeout_ms:
            sleep_device()