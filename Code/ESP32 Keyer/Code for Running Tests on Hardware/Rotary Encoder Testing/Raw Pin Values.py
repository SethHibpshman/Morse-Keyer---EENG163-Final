from machine import Pin
import time

clk = Pin(4, Pin.IN, Pin.PULL_UP)
dt = Pin(47, Pin.IN, Pin.PULL_UP)
sw = Pin(45, Pin.IN, Pin.PULL_UP)

print("Pin watcher running")

last_clk = clk.value()
last_dt = dt.value()
last_sw = sw.value()

while True:
    current_clk = clk.value()
    current_dt = dt.value()
    current_sw = sw.value()

    if current_clk != last_clk or current_dt != last_dt or current_sw != last_sw:
        print(f'CLK: {current_clk}, DT: {current_dt}, SW: {current_sw}')
        last_clk = current_clk
        last_dt = current_dt
        last_sw = current_sw

    # tiny yield to prevent S3 crash
    time.sleep_ms(1)
