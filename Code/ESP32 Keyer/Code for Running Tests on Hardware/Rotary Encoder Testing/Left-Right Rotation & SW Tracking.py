from machine import Pin
import time

clk = Pin(4, Pin.IN, Pin.PULL_UP)
dt = Pin(47, Pin.IN, Pin.PULL_UP)
sw = Pin(45, Pin.IN, Pin.PULL_UP)

# store last states
last_clk = clk.value()
last_dt = dt.value()
last_sw = sw.value()

# counters
right_turns = 0
left_turns = 0
sw_presses = 0

while True:
    current_clk = clk.value()
    current_dt = dt.value()
    current_sw = sw.value()

    # Detect rotation
    if last_clk == 0 and current_clk == 1:  # rising edge on CLK
        if current_dt == 0:
            right_turns += 1  # flipped
            print("Right turn:", right_turns)
        else:
            left_turns += 1   # flipped
            print("Left turn:", left_turns)

    # Detect button press
    if last_sw == 1 and current_sw == 0:  # press detected
        sw_presses += 1
        print("SW pressed:", sw_presses)

    # update last values
    last_clk = current_clk
    last_dt = current_dt
    last_sw = current_sw

    # tiny delay to prevent ESP32S3 crash
    time.sleep_ms(1)
