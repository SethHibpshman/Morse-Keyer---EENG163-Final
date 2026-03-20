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
    time.sleep(dit_t)
    buz.duty_u16(0)
    time.sleep(gap_t)

def do_a_dah():
    buz.duty_u16(16384)
    time.sleep(dah_t)
    buz.duty_u16(0)
    time.sleep(gap_t)  


# <><><><><><><><><><><>
# MAIN LOOP
# <><><><><><><><><><><>

while True:
    if dit_in.value() == 0 and dah_in.value() == 0:
        do_a_dit()
        do_a_dah()
    elif dit_in.value() == 0:
        do_a_dit()
    elif dah_in.value() == 0:
        do_a_dah()

        
