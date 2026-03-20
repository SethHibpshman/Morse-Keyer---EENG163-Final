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
oled = ssd1306.SSD1306_I2C(128, 32, i2c)

# SOFTWARE ##############################
# Timing
dit_t = 0.12 # ~10 Words-Per-Minute
dah_t = dit_t * 3
gap_t = dit_t

# Display Perameters
morse_oled_content = '' # Object where all morse code keyed is held
max_characters = 16 # How many morse characters will be printed on the OLED. 16 is max width of SSD1306

# <><><><><><><><><><><><><><><><><><><><><><>
# FUNCTIONS
# <><><><><><><><><><><><><><><><><><><><><><>

# When a dit is called, the following will happen
def do_a_dit():
    global morse_oled_content
    buz.duty_u16(16384)
    led.value(1)
    morse_oled_content = morse_oled_content + '.' # Adds a dit to the end of the orse_oled_content string.
    draw_morse_oled(morse_oled_content, keying_mode)
    sleep(dit_t)
    buz.duty_u16(0)
    led.value(0)
    sleep(gap_t)

# When a dah is called, the following will happen
def do_a_dah():
    global morse_oled_content
    buz.duty_u16(16384)
    led.value(1)
    morse_oled_content = morse_oled_content + '-' # Adds a dah to the end of the orse_oled_content string.
    draw_morse_oled(morse_oled_content, keying_mode) 
    sleep(dah_t)
    buz.duty_u16(0)
    led.value(0)
    sleep(gap_t)  

# Displays the last 'max_characters' (currently 16 for 128/32px screen) of the morse code on the OLED.
def draw_morse_oled(morse_oled_content=None, mode=None):
    oled.fill(0)
    if morse_oled_content is not None:
        oled.text(morse_oled_content[-max_characters:], 0, 0)
    if mode is not None:
        oled.text(mode, 0 , 12)
    oled.show()

# Mode setup
keying_mode = 'iambic_a' # Default mode
keying_modes = ['iambic_a', 'iambic_b', 'ultimatic', 'straight_key']

# <><><><><><><><><><><><><><><><><><><><><><>
# MAIN LOOP
# <><><><><><><><><><><><><><><><><><><><><><>
# 'last_d' holds the last signal value ('dit' or 'dah').
# Starting value of 'last_d' doesn't really matter because it is instantly rewritten.

# WHAT DO I CALL THIS???? ###############
oled.fill(0)
draw_morse_oled(morse_oled_content, keying_mode)
md_crnt_indx = 0
bth_hld = False # Both buttons held?
bth_hld_prev = False
dit_hold_start_time = 0
dah_hold_start_time = 0
dit_held = False
dah_held = False
last_d = 'dit' # While not strictly necessary, this makes it never undefined.

while True:
# REFRESH ON LOOP START #################
    dit_val = dit_in.value() == 0 # Set dit_val to True if the DIT paddle is currently pressed.
    dah_val = dah_in.value() == 0
    mode_pressed = mode_toggle.value() == 0
    current_time = ticks_ms()

# STATE TRACKING ########################
    if dit_val == True and dit_held == False:
        dit_hold_start_time = current_time
        dit_held = True
    if dah_val == True and dah_held == False:
        dah_hold_start_time = current_time
        dah_held = True
    if dit_val == False:
        dit_held = False
    if dah_val == False:
        dah_held = False

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
    elif keying_mode == 'iambic_a':
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
    elif keying_mode == 'iambic_b':
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
    if keying_mode == 'ultimatic':
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
    if keying_mode == 'straight_key':
        if dit_val or dah_val:
            buz.duty_u16(16384)
            led.value(1)
        else:
            buz.duty_u16(0)
            led.value(0)