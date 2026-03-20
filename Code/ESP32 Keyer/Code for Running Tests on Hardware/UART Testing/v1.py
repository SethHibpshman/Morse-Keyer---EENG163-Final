from machine import UART, Pin
from time import sleep, ticks_ms

# ----------------------------
# UART1 on GPIO17 (TX) / 18 (RX)
# ----------------------------
uart = UART(1, baudrate=115200, tx=17, rx=18)
rx_buf = b""

counter = 0

while True:
    # attach timestamp to message
    timestamp = ticks_ms()
    message = f"MSG {counter} @ {timestamp}ms\n"
    uart.write(message.encode('utf-8'))
    counter += 1

    # non-blocking receive
    if uart.any():
        rx_buf += uart.read()
        if b"\n" in rx_buf:
            line, rx_buf = rx_buf.split(b"\n", 1)
            print(f"RX: {line.decode('utf-8')}")

    sleep(0.1)