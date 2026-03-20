from machine import Pin, SoftI2C, PWM
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
settings_menu_items = ["WPM", "Mode", "Volume", "LED", "Keying Mode", "Decoding", "Buzzer"]
# Values corisponding to each menu item.
settings_menu_values = [
    10,                       # WPM
    ['Training', 'Sandbox'],  # Mode
    5,                        # Volume
    False,                    # LED
    ['Iambic A', 'Iambic B', 'Ultimatic', 'Straight Key'],  # Keying Mode
    False,                    # Decoding
    True                      # Buzzer
]
settings_menu_selected = 0            # Currently highlighted menu item. Starts at index 0.
settings_menu_scroll = 0              # Vertical text offset (scrolling)
settings_menu_line_height = 10        # in pixels
settings_menu_max_visible_lines = 6
settings_menu_in_scrollable_menu = 0  # In scrolling mode of the settings menu. Zero and one because they are easy to compare and save memory.
settings_menu_in_editing_menu = 1                         # In editing menu of the settings menu.
settings_menu_current_menu_mode = settings_menu_in_scrollable_menu  # start in scroll mode

# SOFTWARE ##############################
# Timing
dit_t = 0.12               # Dit time length (in seconds)
dah_t = dit_t * 3          # Dah time length
gap_t = dit_t              # Time between character sounding
letter_break_t = dit_t * 3 # How long to wait until it is considered a new character.
word_break_t = dit_t * 7   # How long to wait until it is considered a new word.
wpm_static_max = 1200 / (dit_t * 1000) # Based upon a 50 dit duration standard word such as PARIS, the time for one dit duration or one unit can be computed by the formula.

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
    buz.duty_u16(16384)
    led.value(1)
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
    buz.duty_u16(16384)
    led.value(1)
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
    global wpm_static_max
    oled.fill(0)
    if morse_oled_content is not None:
        oled.text('Morse:', 0, 0)
        draw_right_aligned((morse_oled_content[-max_characters:]), 128, 12)
        draw_right_aligned((decoded_text[-max_characters:]), 128, 24)
        draw_right_aligned(f'WPM: {int(wpm_static_max)}', 128, 48)
    oled.show()

def settings_menu_draw_menu():
    oled.fill(0)
    # If in the editing mode of the settings menu, draw the setting you're editing and what the value of it currently is.
    if settings_menu_current_menu_mode == settings_menu_in_editing_menu:
        currently_selected_menu_item = settings_menu_items[settings_menu_selected]
        value_of_currently_selected_menu_item  = value_to_str(settings_menu_selected, settings_menu_values[settings_menu_selected])
        draw_centered(currently_selected_menu_item, 64, 18)
        draw_centered(value_of_currently_selected_menu_item, 64, 36)
        oled.show()
        return
    # If in the scrollable settings menu, if the highlighted item is above/below the scrolling index, change the scrolling index to the new selected item so that the settings menu scrolls downward.
    global settings_menu_scroll
    if settings_menu_selected < settings_menu_scroll:
        settings_menu_scroll = settings_menu_selected
    elif settings_menu_selected >= settings_menu_scroll + settings_menu_max_visible_lines:
        settings_menu_scroll = settings_menu_selected - settings_menu_max_visible_lines + 1
    # The actual drawing part.
    # i is the index of the menu item.
    # This for loop only iterates through the items that should be drawn.
    # For example, if there are 7 menu items, and only 6 lines of vertical space, it will only iterate the 6 lines starting from the index of the menu item that is currently highlighted.
    for i in range(settings_menu_scroll, min(settings_menu_scroll + settings_menu_max_visible_lines, len(settings_menu_items))):
        y = (i - settings_menu_scroll) * settings_menu_line_height # The vertical pixel coordinate where the menu item should be drawn.
        # Doesn't draw anything that wouldn't fit on the screen.
        if y + settings_menu_line_height > 64:
            continue
        # The text for the currently selected menu item is the index of the iteration.
        currently_selected_menu_item = settings_menu_items[i]
        # If it is the selected menu item, highlight it with the graphics library.
        if i == settings_menu_selected:
            oled_gfx.fill_rect(0, y, 128, settings_menu_line_height, 1)
            oled.text(currently_selected_menu_item, 4, y + 1, 0)
        # Else draw normal.
        else:
            oled.text(currently_selected_menu_item, 4, y + 1, 1)
    oled.show()

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

def value_to_str(idx, menu_value):
    # Some menu items are bools, str, or ints. Converts all to strings.
    if idx in [3, 5, 6]:  # LED, Decoding, Buzzer indicies (Boolean settings).
        if menu_value:
            return 'Enabled'
        else:
            return 'Disabled'
    if type(menu_value) == list:
        return menu_value[0] # See notes elsewhere where menu_value is dynamically selected. This just returns the first item in the list.
    return str(menu_value) # For all other types, directly convert to string.

def rotary_encoder_handler(delta):
    # Delta is equal to how many times the encoder has rotated. (+1 clockwise, -1 counter-clockwise)
    global settings_menu_selected
    # If in the scrollable menu, scroll through menu items
    if settings_menu_current_menu_mode == settings_menu_in_scrollable_menu:
        settings_menu_selected = (settings_menu_selected + delta) % len(settings_menu_items)
    # If in the editing mode of the settings, menu, cycle through the settings values.
    elif settings_menu_current_menu_mode == settings_menu_in_editing_menu:
        menu_value = settings_menu_values[settings_menu_selected]
        # Edit values like before
        if settings_menu_selected == 0:  # WPM
            settings_menu_values[settings_menu_selected] = min(max(10, menu_value + delta), 40) # Range of 10-40 (Called 'clamping')
        elif settings_menu_selected == 2:  # Volume
            settings_menu_values[settings_menu_selected] = min(max(0, menu_value + delta), 10) # Range of 0-10
        elif settings_menu_selected in [3, 5, 6]:  # LED, Decoding, Buzzer
            if delta != 0:
                settings_menu_values[settings_menu_selected] = not menu_value # Swap between True and False
        # This is the difficult shit...
        elif settings_menu_selected in [1, 4]:  # is Mode, Keying Mode
            idx = menu_value.index(menu_value[0])  # This one is kinda weird. It takes the value of an index and searches the list for that value and saves that index into idx.
            idx = (idx + delta) % len(menu_value) # Modulo allows the wrap around of the list.
            menu_value.insert(0, menu_value.pop(idx)) # Finds the idx and moves it to the front. This means that scrolling (+-delta will swap around the list and put the selected item in index 0). 'menu_value[0]' is the active choice for all other code.
            settings_menu_values[settings_menu_selected] = menu_value # Replaces the old list in the master list with the new list.

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
keying_modes = ['Iambic A', 'Iambic B', 'Ultimatic', 'Straight Key']
md_crnt_indx = 0 # Default keying mode
keying_mode = keying_modes[md_crnt_indx]

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
                settings_menu_selected = 0
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