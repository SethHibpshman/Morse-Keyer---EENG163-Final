import time
from machine import Pin, UART, SPI
from time import sleep
from lcd9341 import LCD9341, color565
from xfglcd_font import XglcdFont

# <><><><><><><><><><><><><><>
# STM32 LCD setup
# <><><><><><><><><><><><><><>
LCD_SPI_BUS = 5
SPI5_BAUD_RATE = 10_000_000
spi = SPI(LCD_SPI_BUS, baudrate=SPI5_BAUD_RATE)
lcd = LCD9341(spi, dc=Pin('PD13'), cs=Pin('PC2'), rst=Pin('PC11'))
unispace = XglcdFont('fonts/Unispace12x24.c', 12, 24)

# <><><><><><><><><><><><><><>
# UART setup
# <><><><><><><><><><><><><><>
uart = UART(1, 115200)
rx_buf = b""

# <><><><><><><><><><><><><><>
# Layout
# <><><><><><><><><><><><><><>
CHAR_WIDTH    = 12
CHAR_HEIGHT   = 24
DISPLAY_CHARS = 20

TEXT_X  = 0
LINE1_Y = 0                            # "Morse RX:" static label
LINE2_Y = CHAR_HEIGHT                  # received text, one line below

TEXT_W  = CHAR_WIDTH * DISPLAY_CHARS   # 240 px — full width
TEXT_H  = CHAR_HEIGHT                  # 24 px

BG_COLOR = color565(0,   0,   0)
FG_COLOR = color565(255, 255, 255)

last_drawn = None

# <><><><><><><><><><><><><><>
# Draw — only line 2 is ever redrawn
# <><><><><><><><><><><><><><>
def draw_morse(text):
    global last_drawn
    snippet = text[-DISPLAY_CHARS:]
    while len(snippet) < DISPLAY_CHARS:
        snippet = snippet + " "
    if snippet == last_drawn:
        return
    last_drawn = snippet
    for row in range(TEXT_H):
        lcd.draw_hline(TEXT_X, LINE2_Y + row, TEXT_W, BG_COLOR)
    lcd.draw_text(TEXT_X, LINE2_Y, snippet, unispace, FG_COLOR)

# <><><><><><><><><><><><><><>
# Init
# <><><><><><><><><><><><><><>
lcd.clear(BG_COLOR)
lcd.draw_text(TEXT_X, LINE1_Y, "Morse RX:", unispace, FG_COLOR)  # static, drawn once
draw_morse("")

# <><><><><><><><><><><><><><>
# Main loop
# <><><><><><><><><><><><><><>
morse_content = ""

while True:
    if uart.any():
        rx_buf += uart.read()
        while b"\n" in rx_buf:
            line, rx_buf = rx_buf.split(b"\n", 1)
            try:
                decoded = line.decode('utf-8').strip()
            except UnicodeError:
                continue
            if decoded:
                morse_content = decoded
                draw_morse(morse_content)
    sleep(0.01)
