from machine import Pin, SoftI2C, PWM, soft_reset
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
    ("Keying Mode", "keying_mode"),
    ("BEHAVIOR", "heading"),
    ("Volume", "volume"),
    ("LED", "led"),
    ("Decoding", "decoding"),
    ("OTHER", "heading"),
    ("About", "about"),
    ("Reset", "reset"),
]
settings = { # Values corisponding to each menu item. These are default values.
    "wpm": 10,
    "mode": 0,
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

# SOFTWARE ##############################
# Display Perameters
morse_oled_content = '' # Object where all morse code keyed is held
decoded_text = ''
max_characters = 16 # How many morse characters will be printed on the OLED. 16 is max width of SSD1306

# <><><><><><><><><><><><><><><><><><><><><><>
# FUNCTIONS
# <><><><><><><><><><><><><><><><><><><><><><>

# When a dit is called, the following will happen
def do_a_dit():
    global morse_oled_content, last_morse_end_time
    buz.duty_u16(buz_volume)
    led.value(settings["led"])  # Reads dictionary to see if the LED is enabled.
    morse_oled_content = morse_oled_content + '.' # Adds a dit to the end of the orse_oled_content string.
    draw_morse_oled(morse_oled_content)
    sleep(dit_t)
    buz.duty_u16(0)
    led.value(0)
    sleep(gap_t)
    last_morse_end_time = ticks_ms()

# When a dah is called, the following will happen
def do_a_dah():
    global morse_oled_content, last_morse_end_time
    buz.duty_u16(buz_volume)
    led.value(settings["led"])
    morse_oled_content = morse_oled_content + '-' # Adds a dah to the end of the orse_oled_content string.
    draw_morse_oled(morse_oled_content)
    sleep(dah_t)
    buz.duty_u16(0)
    led.value(0)
    sleep(gap_t)
    last_morse_end_time = ticks_ms()

def draw_centered(text, center_x, y):
    width = len(text) * 8
    x = center_x - (width // 2)
    oled.text(text, x, y)

def draw_right_aligned(text, right_x, y):
    width = len(text) * 8  # 8 pixels per character
    x = right_x - width
    oled.text(text, x, y)

# Displays the last 'max_characters' (currently 16 for 128/64px screen) of the morse code on the OLED.
def draw_morse_oled(morse_oled_content=None):
    oled.fill(0)
    if morse_oled_content is not None:
        oled.text('Morse:', 0, 0)
        draw_right_aligned((morse_oled_content[-max_characters:]), 128, 12)
        draw_right_aligned((decoded_text[-max_characters:]), 128, 24)
    oled.show()

def reset():
    oled.fill(0)
    draw_centered("Resetting", 64, 28)
    oled.show()
    sleep(0.5)
    oled.fill(0)
    draw_centered("Resetting.", 64, 28)
    oled.show()
    sleep(0.5)
    oled.fill(0)
    draw_centered("Resetting..", 64, 28)
    oled.show()
    sleep(0.5)
    oled.fill(0)
    draw_centered("Resetting...", 64, 28)
    oled.show()
    sleep(0.5)
    soft_reset()

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
            reset()
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

about_scroll_offset = 0  # How much the screen has scrolled through the text lines.
about_scroll_speed = 8   # pixels per update
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
    index_last_slash = morse_oled_content.rfind('/')
    index_last_space = morse_oled_content.rfind(' ')
    last_break_index = max(index_last_slash, index_last_space)
    last_morse_letter = morse_oled_content[last_break_index+1:int(len(morse_oled_content))]
    if morse_dictionary.get(last_morse_letter):
        decoded_text = decoded_text + morse_dictionary.get(last_morse_letter)
    # If entry not found in dictionary, print the character that represents null.
    else:
        if decoded_text == '':
            pass
        else:
            decoded_text = decoded_text + '?'

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
            draw_morse_oled(morse_oled_content)
            letter_space_happened = True
            word_space_happened = False

        # WORD GAP counts time since last letter space
        if letter_space_happened == True and word_space_happened == False:
            if idle_time >= int((word_break_t) * 1000):
                # Edits the space to be a slash if the idle is longer than a word break.
                if morse_oled_content and morse_oled_content[-1] == ' ':
                    morse_oled_content = morse_oled_content[:-1] + '/'
                    decoded_text = decoded_text + ' '
                draw_morse_oled(morse_oled_content)
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

        # If the key is not one of these, it is not editable.
        if key not in ["mode", "keying_mode", "volume", "led", "decoding", "wpm"]:
            return  # ignore action items like "about"/"reset"

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

# <><><><><><><><><><><><><><><><><><><><><><>
# DATABASES & DICTIONARIES
# <><><><><><><><><><><><><><><><><><><><><><>
morse_dictionary = {
    # Taken from https://en.wikipedia.org/wiki/Morse_code
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

# <><><><><><><><><><><><><><><><><><><><><><>
# INITIALIZATION
# <><><><><><><><><><><><><><><><><><><><><><>
# Clear Screen
oled.fill(0)

# Keying Mode Setup
modes = ['Training', 'Sandbox']
keying_modes = ['Iambic A', 'Iambic B', 'Ultimatic', 'Straight Key']

# Draw Elements on Screen
settings_menu_draw_menu()

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
    # Keying Mode
    keying_mode = keying_modes[settings["keying_mode"]]

    # Menu Handling #################
    # Continue business as normal if the settings menu isn't open.
    if not settings_menu_open:
        draw_morse_oled(morse_oled_content)

    # BUTTON STATE TRACKING ############################################
    # DIT BUTTON ############################
    if dit_val == True and dit_held == False:
        # Tracks when it is being held and when it was first held down.
        dit_hold_start_time = current_time
        dit_held = True
    elif dit_val == False and dit_held == True:
        # When released, it will know because it is not held down, but dit_held is true. Tracks when released and resets held.
        dit_held = False
        dit_release_time = current_time

    # DAH BUTTON ############################
    if dah_val == True and dah_held == False:
        # Tracks when it is being held and when it was first held down.
        dah_hold_start_time = current_time
        dah_held = True
    elif dah_val == False and dah_held == True:
        # When released, it will know because it is not held down, but dit_held is true. Tracks when released and resets held.
        dah_held = False
        dah_release_time = current_time

    # IAMBIC A ##############################
    elif keying_mode == 'Iambic A':
        # When both buttons pressed, alternate dits and dahs.
        if dit_val and dah_val: 
            if last_d == 'dah':
                do_a_dit()
                last_d = 'dit'
            else:
                do_a_dah()
                last_d = 'dah'
        # Do a dit and set last to dit
        elif dit_val: 
            do_a_dit()
            last_d = 'dit'
        # Do a dah and set last to dah.
        elif dah_val: 
            do_a_dah()
            last_d = 'dah'

    # IAMBIC B ##############################
    elif keying_mode == 'Iambic B':
        # When both buttons pressed, alternate dits and dahs.
        if dit_val and dah_val:
            bth_hld = True # Both buttons held
            if last_d == 'dah':
                do_a_dit()
                last_d = 'dit'
            else:
                do_a_dah()
                last_d = 'dah'
        
        # Extra dit/dash after release
        elif bth_hld_prev == True:  
            if last_d == 'dah':
                do_a_dit()
                last_d = 'dit'
            else:
                do_a_dah()
                last_d = 'dah'
            
            
        # Do a dit and set last to dit
        elif dit_val: 
            do_a_dit()
            last_d = 'dit'
        # Do a dah and set last to dah.
        elif dah_val: 
            do_a_dah()
            last_d = 'dah'

        bth_hld_prev = bth_hld
        bth_hld = False

    # ULTIMATIC #############################
    if keying_mode == 'Ultimatic':
        # When both buttons pressed, repeat last pressed.
        if dit_val and dah_val: 
            if dit_hold_start_time < dah_hold_start_time:
                do_a_dah()
            elif dit_hold_start_time > dah_hold_start_time:
                do_a_dit()
        # Do a dit and set last to dit
        elif dit_val: 
            do_a_dit()
            last_d = 'dit'
        # Do a dah and set last to dah.
        elif dah_val: 
            do_a_dah()
            last_d = 'dah'

    # STRAIGHT KEY ##########################
    if keying_mode == 'Straight Key':
        if dit_val or dah_val:
            buz.duty_u16(16384)
            led.value(1)
        else:
            buz.duty_u16(0)
            led.value(0)

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
                settings_menu_draw_menu()
    last_clk = current_clk

    # DECODING ########################################################
    gap_checker() # Inserts spaces (letter breaks) or slashes (word breaks) depending on input idleness.