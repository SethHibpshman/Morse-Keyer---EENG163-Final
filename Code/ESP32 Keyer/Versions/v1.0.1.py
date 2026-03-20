from machine import Pin, SoftI2C, PWM
import ssd1306
from time import sleep

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
    draw_morse_oled()
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
    draw_morse_oled()
    sleep(dah_t)
    buz.duty_u16(0)
    led.value(0)
    sleep(gap_t)  

# Displays the last 'max_characters' (currently 16 for 128/32px screen) of the morse code on the OLED.
def draw_morse_oled():
    oled.fill(0)
    oled.text(morse_oled_content[-max_characters:], 0, 0)
#    print(morse_oled_content)
    oled.show()
    
# <><><><><><><><><><><><><><><><><><><><><><>
# MAIN LOOP
# <><><><><><><><><><><><><><><><><><><><><><>

# 'last_d' holds the last signal value ('dit' or 'dah').
# Starting value doesn't really matter because it is instantly rewritten.
oled.fill(0)

while True:
    dit_val = dit_in.value() == 0 # Set dit_val to True if the DIT paddle is currently pressed.
    dah_val = dah_in.value() == 0
    
    if dit_val and dah_val: # When both buttons pressed, alternate dits and dahs.
        if last_d == 'dah':
            do_a_dit()
            last_d = 'dit'
        else:
            do_a_dah()
            last_d = 'dah'
            
    elif dit_val: # Do a dit and set last to dit
        do_a_dit()
        last_d = 'dit'
    elif dah_val: # Do a dah and set last to dah.
        do_a_dah()
        last_d = 'dah'