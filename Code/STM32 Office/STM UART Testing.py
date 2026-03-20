import time
from machine import Pin, UART, SoftI2C, SPI
from time import sleep, ticks_ms
from lcd9341 import LCD9341, color565
from xfglcd_font import XglcdFont

# -----------------------------
# STM32 LCD setup (template)
# -----------------------------
LCD_SPI_BUS = 5
SPI5_BAUD_RATE = 10_000_000
spi = SPI(LCD_SPI_BUS, baudrate=SPI5_BAUD_RATE)
lcd = LCD9341(spi, dc=Pin('PD13'), cs=Pin('PC2'), rst=Pin('PC11'))
unispace = XglcdFont('fonts/Unispace12x24.c', 12, 24)

# -----------------------------
# UART1 setup (PA9=TX, PA10=RX)
# -----------------------------
uart = UART(1, 115200)
rx_buf = b""

counter = 0

# Screen rectangle for UART output
RECT_X = 10
RECT_Y = 10
RECT_W = 220
RECT_H = 64
CHAR_WIDTH = 12
CHAR_HEIGHT = 24
MAX_CHARS_PER_LINE = RECT_W // CHAR_WIDTH
MAX_LINES = RECT_H // CHAR_HEIGHT

def draw_lines(lines):
    # Clear rectangle
    lcd.draw_rectangle(RECT_X, RECT_Y, RECT_W, RECT_H, color565(0, 0, 0))
    lcd.draw_rectangle(RECT_X, RECT_Y, RECT_W, RECT_H, color565(255, 255, 255))
    for i, line in enumerate(lines[:MAX_LINES]):
        lcd.draw_text(RECT_X + 2, RECT_Y + 2 + i * CHAR_HEIGHT, line, unispace, color565(255, 255, 255))

# <><><><><><><><><><><><><><>
# Main loop
# <><><><><><><><><><><><><><>
lcd.clear(color565(0, 0, 0))
lcd.draw_text(20, 40, "LCD OK", unispace, color565(255, 255, 255))
sleep(1)

while True:
    if uart.any():
        rx_buf += uart.read()

        while b"\n" in rx_buf:
            line, rx_buf = rx_buf.split(b"\n", 1)

            try:
                morse = line.decode('utf-8').strip()
            except:
                continue

            display_msg = "Morse: " + morse

            wrapped = [
                display_msg[i:i + MAX_CHARS_PER_LINE]
                for i in range(0, len(display_msg), MAX_CHARS_PER_LINE)
            ]

            draw_lines(wrapped)

    sleep(0.01)

