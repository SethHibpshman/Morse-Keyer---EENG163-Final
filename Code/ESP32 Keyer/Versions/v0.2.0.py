from machine import Pin, PWM
import time


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


# <><><><><><><><><><><>
# FUNCTIONS
# <><><><><><><><><><><>

def do_a_dit():
    buz.duty_u16(16384)
    print('.', end='')
    time.sleep(dit_t)
    buz.duty_u16(0)
    time.sleep(gap_t)

def do_a_dah():
    buz.duty_u16(16384)
    print('-', end='')
    time.sleep(dah_t)
    buz.duty_u16(0)
    time.sleep(gap_t)  


# <><><><><><><><><><><>
# MAIN LOOP
# <><><><><><><><><><><>

last_d = 'dah' # 'last_d' holds the last signal value ('dit' or 'dah'). Starts with 'dah'.

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