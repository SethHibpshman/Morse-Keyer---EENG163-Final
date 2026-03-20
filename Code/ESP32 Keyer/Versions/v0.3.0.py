from machine import Pin, SoftI2C, PWM
import ssd1306
from time import sleep

# <><><><><><><><><><><>
# INITIAL SETUP
# <><><><><><><><><><><>

# TIMING
dit_t = 0.12 # ~10 Words-Per-Minute
dah_t = dit_t * 3
gap_t = dit_t

# HARDWARE
buz = PWM(Pin(1)) # Buzzer
buz.freq(700)
buz.duty_u16(0)

dit_in = Pin(16, Pin.IN, Pin.PULL_UP) # Buttons
dah_in = Pin(7, Pin.IN, Pin.PULL_UP)

led = Pin(38, Pin.OUT) # External LED

i2c = SoftI2C(scl=Pin(46), sda=Pin(8)) # SSD1306 screen setup
oled = ssd1306.SSD1306_I2C(128, 32, i2c)

# <><><><><><><><><><><>
# FUNCTIONS
# <><><><><><><><><><><>

def do_a_dit():
    global morse_oled_content
    buz.duty_u16(16384)
    led.value(1)
    morse_oled_content = morse_oled_content + '.'
    draw_morse_oled()
    sleep(dit_t)
    buz.duty_u16(0)
    led.value(0)
    sleep(gap_t)

def do_a_dah():
    global morse_oled_content
    buz.duty_u16(16384)
    led.value(1)
    morse_oled_content = morse_oled_content + '-'
    draw_morse_oled()
    sleep(dah_t)
    buz.duty_u16(0)
    led.value(0)
    sleep(gap_t)  

morse_oled_content = ''
max_characters = 16
def draw_morse_oled():
    oled.fill(0)
    oled.text(morse_oled_content[-max_characters:], 0, 0)
#    print(morse_oled_content)
    oled.show()
    

# <><><><><><><><><><><>
# MAIN LOOP
# <><><><><><><><><><><>

last_d = 'dah' # 'last_d' holds the last signal value ('dit' or 'dah'). Starts with 'dah'.
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