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
mode_toggle = Pin(6, Pin.IN, Pin.PULL_UP)

# External LED
led = Pin(38, Pin.OUT)

# SSD1306 screen setup
i2c = SoftI2C(scl=Pin(46), sda=Pin(8))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

oled_gfx = gfx.GFX(128, 64, oled.pixel)

# SOFTWARE ##############################
# Timing
dit_t = 0.12  # Dit time length (in seconds)
dah_t = dit_t * 3  # Dah time length
gap_t = dit_t  # Time between character sounding
letter_break_t = dit_t * 3  # How long to wait until it is considered a new character.
word_break_t = dit_t * 7  # How long to wait until it is considered a new word.
wpm_static_max = 1200 / (dit_t * 1000)  # Based upon a 50 dit duration standard word such as PARIS, the time for one dit duration or one unit can be computed by the formula.

# Display Perameters
morse_oled_content = ''  # Object where all morse code keyed is held
decoded_text = ''
max_characters = 16  # How many morse characters will be printed on the OLED. 16 is max width of SSD1306


# <><><><><><><><><><><><><><><><><><><><><><>
# FUNCTIONS
# <><><><><><><><><><><><><><><><><><><><><><>

# When a dit is called, the following will happen
def do_a_dit():
    global morse_oled_content, last_morse_end_time
    buz.duty_u16(16384)
    led.value(1)
    morse_oled_content = morse_oled_content + '.'  # Adds a dit to the end of the orse_oled_content string.
    draw_morse_oled(morse_oled_content, keying_mode)
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
    morse_oled_content = morse_oled_content + '-'  # Adds a dah to the end of the orse_oled_content string.
    draw_morse_oled(morse_oled_content, keying_mode)
    sleep(dah_t)
    buz.duty_u16(0)
    led.value(0)
    sleep(gap_t)
    last_morse_end_time = ticks_ms()


def draw_right_aligned(text, right_x, y):
    width = len(text) * 8  # 8 pixels per character
    x = right_x - width
    oled.text(text, x, y)


# Displays the last 'max_characters' (currently 16 for 128/64px screen) of the morse code on the OLED.
def draw_morse_oled(morse_oled_content=None, mode=None):
    global wpm_static_max
    oled.fill(0)
    oled_gfx.hline(0, 34, 128, 1)
    if morse_oled_content is not None:
        oled.text('Morse:', 0, 0)
        draw_right_aligned((morse_oled_content[-max_characters:]), 128, 12)
        draw_right_aligned((decoded_text[-max_characters:]), 128, 24)
        draw_right_aligned('WPM:', 128, 36)
        draw_right_aligned(f'{int(wpm_static_max)}', 128, 48)
    if mode is not None:
        oled.text('Mode:', 0, 36)
        oled.text(f'{mode}', 0, 48)
    oled.show()


def morse_decoder():
    global decoded_text
    index_last_slash = morse_oled_content.rfind('/')
    index_last_space = morse_oled_content.rfind(' ')
    last_break_index = max(index_last_slash, index_last_space)
    last_morse_letter = morse_oled_content[last_break_index + 1:int(len(morse_oled_content))]
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
        idle_time = ticks_diff(current_time, idle_start_time)  # Updates how long it's been idle.

        # (Convert letter_break_t to milliseconds)
        # If the idle time exceeds the letter break perameter and a space hasn't already been printed, print one.
        if idle_time >= int(letter_break_t * 1000) and letter_space_happened == False:
            morse_decoder()
            morse_oled_content = morse_oled_content + ' '
            draw_morse_oled(morse_oled_content, keying_mode)
            letter_space_happened = True
            word_space_happened = False

        # WORD GAP counts time since last letter space
        if letter_space_happened == True and word_space_happened == False:
            if idle_time >= int((word_break_t) * 1000):
                # Edits the space to be a slash if the idle is longer than a word break.
                if morse_oled_content and morse_oled_content[-1] == ' ':
                    morse_oled_content = morse_oled_content[:-1] + '/'
                    decoded_text = decoded_text + ' '
                draw_morse_oled(morse_oled_content, keying_mode)
                word_space_happened = True
    else:
        # If buttons being pressed, then no breaks, and say it's not idle.
        idle_start_time = 0
        letter_space_happened = False
        word_space_happened = False


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
    ".-.-.-": ".",  # Period
    "--..--": ",",  # Comma
    "..--..": "?",  # Question mark
    ".----.": "'",  # Apostrophe
    "-..-.": "/",  # Slash
    "-.--.": "(",  # Open parenthesis
    "-.--.-": ")",  # Close parenthesis
    "---...": ":",  # Colon
    "-.-.-.": ";",  # Semicolon
    "-...-": "=",  # Equals
    ".-.-.": "+",  # Plus
    "-....-": "-",  # Hyphen
    ".-..-.": "\"",  # Quotation mark
    ".--.-.": "@",  # At sign
    "-.-.--": "!",  # Exclamation
    "..--.-": "_",  # Underscore
    "...-..-": "$",  # Dollar
}

# <><><><><><><><><><><><><><><><><><><><><><>
# INITIALIZATION
# <><><><><><><><><><><><><><><><><><><><><><>
# Clear Screen
oled.fill(0)

# Keying Mode Setup
keying_modes = ['Iambic A', 'Iambic B', 'Ultimatic', 'Straight Key']
md_crnt_indx = 0  # Default keying mode
keying_mode = keying_modes[md_crnt_indx]

# Draw Elements on Screen
draw_morse_oled(morse_oled_content, keying_mode)

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
    dit_val = dit_in.value() == 0  # Set dit_val to True if the DIT paddle is currently pressed.
    dah_val = dah_in.value() == 0
    mode_pressed = mode_toggle.value() == 0
    current_time = ticks_ms()
    draw_morse_oled(morse_oled_content, keying_mode)

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

    # MODE STUFF ########################################################
    # SWAP MODES ############################
    if mode_pressed:
        md_crnt_indx = (md_crnt_indx + 1) % len(keying_modes)  # Mode_Current_Index
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
            bth_hld = True  # Both buttons held
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
    gap_checker()  # Inserts spaces (letter breaks) or slashes (word breaks) depending on input idleness.