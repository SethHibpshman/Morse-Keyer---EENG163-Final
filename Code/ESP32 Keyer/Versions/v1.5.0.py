from machine import Pin, SoftI2C, PWM
import ssd1306
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
mode_toggle = Pin(6, Pin.IN, Pin.PULL_UP)

# External LED
led = Pin(38, Pin.OUT)

# SSD1306 screen setup
i2c = SoftI2C(scl=Pin(46), sda=Pin(8)) 
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# SOFTWARE ##############################
# Timing
dit_t = 0.12               # Dit time length (in seconds)
dah_t = dit_t * 3          # Dah time length
gap_t = dit_t              # Time between character sounding
letter_break_t = dit_t * 3 # How long to wait until it is considered a new character.
word_break_t = dit_t * 7  # How long to wait until it is considered a new word.

# Display Perameters
morse_oled_content = '' # Object where all morse code keyed is held
max_characters = 16 # How many morse characters will be printed on the OLED. 16 is max width of SSD1306

# <><><><><><><><><><><><><><><><><><><><><><>
# FUNCTIONS
# <><><><><><><><><><><><><><><><><><><><><><>

# When a dit is called, the following will happen
def do_a_dit():
    global morse_oled_content, last_morse_end_time
    global letter_space_happened, word_space_happened
    buz.duty_u16(16384)
    led.value(1)
    morse_oled_content = morse_oled_content + '.' # Adds a dit to the end of the orse_oled_content string.
    draw_morse_oled(morse_oled_content, keying_mode)
    sleep(dit_t)
    buz.duty_u16(0)
    led.value(0)
    sleep(gap_t)
    last_morse_end_time = ticks_ms()

# When a dah is called, the following will happen
def do_a_dah():
    global morse_oled_content, last_morse_end_time
    global letter_space_happened, word_space_happened
    buz.duty_u16(16384)
    led.value(1)
    morse_oled_content = morse_oled_content + '-' # Adds a dah to the end of the orse_oled_content string.
    draw_morse_oled(morse_oled_content, keying_mode)
    sleep(dah_t)
    buz.duty_u16(0)
    led.value(0)
    sleep(gap_t)
    last_morse_end_time = ticks_ms()

# Displays the last 'max_characters' (currently 16 for 128/64px screen) of the morse code on the OLED.
def draw_morse_oled(morse_oled_content=None, mode=None):
    oled.fill(0)
    if morse_oled_content is not None:
        oled.text('Morse:', 0, 0)
        oled.text(morse_oled_content[-max_characters:], 0, 12)
    if mode is not None:
        oled.text('Mode:', 0 , 36)
        oled.text(f'  {mode}', 0 , 48)
    oled.show()
    
def gap_checker():
    global morse_oled_content
    global idle_start_time, last_letter_time
    global letter_space_happened, word_space_happened

    if not dit_val and not dah_val:
        # Start counting idle time if this is the first idle loop
        if 'idle_start_time' not in globals() or idle_start_time is None:
            idle_start_time = current_time

        # Convert letter_break_t to milliseconds
        idle_time = ticks_diff(current_time, idle_start_time)
        if idle_time >= int(letter_break_t * 1000) and not letter_space_happened:
            morse_oled_content += ' '
            draw_morse_oled(morse_oled_content, keying_mode)
            letter_space_happened = True
            word_space_happened = False
            last_letter_time = current_time

        # WORD GAP counts time since last letter space
        if letter_space_happened and not word_space_happened:
            idle_since_letter = ticks_diff(current_time, last_letter_time)
            if idle_since_letter >= int((word_break_t - letter_break_t) * 1000):
                if morse_oled_content and morse_oled_content[-1] == ' ':
                    morse_oled_content = morse_oled_content[:-1] + '/'
                else:
                    morse_oled_content += '/'
                draw_morse_oled(morse_oled_content, keying_mode)
                word_space_happened = True

    else:
        # A key is pressed → reset idle
        idle_start_time = None
        letter_space_happened = False
        word_space_happened = False


# <><><><><><><><><><><><><><><><><><><><><><>
# DATABASES & DICTIONARIES
# <><><><><><><><><><><><><><><><><><><><><><>
MORSE_DICTIONARY = {
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
    ".-.-.": "+",       # Plus (collides with <RN>)
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
oled.fill(0)

keying_modes = ['Iambic A', 'Iambic B', 'Ultimatic', 'Straight Key']
md_crnt_indx = 0 # Default mode
keying_mode = keying_modes[md_crnt_indx]

draw_morse_oled(morse_oled_content, keying_mode)

bth_hld = False # Both buttons held?
bth_hld_prev = False
dit_hold_start_time = 0
dah_hold_start_time = 0
dit_release_time = 0
dah_release_time = 0
last_morse_end_time = 0
dit_held = False
dah_held = False
last_d = 'dit' # While not strictly necessary, this makes it never undefined.
letter_space_happened = False
word_space_happened = False

# <><><><><><><><><><><><><><><><><><><><><><>
# MAIN LOOP
# <><><><><><><><><><><><><><><><><><><><><><>
while True:
    # REFRESH ON LOOP START #################
    dit_val = dit_in.value() == 0 # Set dit_val to True if the DIT paddle is currently pressed.
    dah_val = dah_in.value() == 0
    mode_pressed = mode_toggle.value() == 0
    current_time = ticks_ms()
    draw_morse_oled(morse_oled_content, keying_mode)

    # BUTTON STATE TRACKING ########################
    # Dit button
    if dit_val == True and dit_held == False:
        # Button just pressed
        dit_hold_start_time = current_time
        dit_held = True
    elif dit_val == False and dit_held == True:
        # Button just released
        dit_held = False
        dit_release_time = current_time  # <-- store release time
    # Dah button
    if dah_val == True and dah_held == False:
        # Button just pressed
        dah_hold_start_time = current_time
        dah_held = True
    elif dah_val == False and dah_held == True:
        # Button just released
        dah_held = False
        dah_release_time = current_time  # <-- store release time

    # MODE STUFF ########################################################
    # SWAP MODES ############################
    if mode_pressed:
        md_crnt_indx = (md_crnt_indx + 1) % len(keying_modes) # Mode_Current_Index
        keying_mode = keying_modes[md_crnt_indx]
        
        buz.freq(1600)
        buz.duty_u16(16384)
        draw_morse_oled(morse_oled_content, keying_mode)
        sleep(0.03)
        
        buz.duty_u16(0)
        buz.freq(700)
        sleep(0.2)

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
# DECODING ########################################################
    gap_checker()