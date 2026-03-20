"""
Morse RX Display - STM32 + ILI9341 LCD
=======================================
Receives morse code strings over UART and displays the last 20 characters
on a 240x320 ILI9341 LCD. Line 1 is a static label; line 2 updates on RX.

Hardware:
    - STM32 microcontroller (MicroPython)
    - ILI9341 LCD via SPI5
    - UART1 (PA9=TX, PA10=RX) at 115200 baud

Classes:
    DisplayDriver  -- manages LCD rendering for the two-line layout
    MorseReceiver  -- handles UART receive, decoding, and display updates
    
Author: Seth Hibpshman
Course: EENG 163 Final Project
License: GNU GPL v3
"""

from machine import Pin, UART, SPI
from time import sleep
from lcd9341 import LCD9341, color565
from xfglcd_font import XglcdFont


# Display constants <><><><><><><><><><><><><><><><><><><><><><><><>

char_width    = 12
char_height   = 24
display_chars = 20          # max chars across the 240 px screen (240 / 12 = 20)

text_x  = 0
line1_y = 0                 # static label row (y pixel offset)
line2_y = char_height       # dynamic morse row (one char-height below label)

text_w  = char_width * display_chars    # 240 px - full screen width
text_h  = char_height                   # 24 px - one character row height

bg_color     = color565(0,   0,   0)
fg_color     = color565(255, 255, 255)

# Hardware init <><><><><><><><><><><><><><><><><><><><><><><><>

spi      = SPI(5, baudrate=10_000_000)
lcd      = LCD9341(spi, dc=Pin('PD13'), cs=Pin('PC2'), rst=Pin('PC11'))
unispace = XglcdFont('fonts/Unispace12x24.c', 12, 24)


# Classes <><><><><><><><><><><><><><><><><><><><><><><><>

class DisplayDriver:
    """
    Manages the two-line ILI9341 LCD layout.

    Line 1 is a static label drawn once at init.
    Line 2 is a 20-character dynamic field, redrawn only when content changes.

    Attributes
    ----------
    lcd : LCD9341
        The LCD driver instance.
    font : XglcdFont
        The font used for all text rendering.
    last_drawn : str or None
        The last string written to line 2; used to skip redundant redraws.

    Methods
    -------
    update(text):
        Update line 2 with the last 20 characters of text.
    """

    def __init__(self, lcd, font, label):
        """
        Initialise the display, clear it, and draw the static label.

        Parameters
        ----------
        lcd : LCD9341
            Initialised LCD driver object.
        font : XglcdFont
            Font object for rendering text.
        label : str
            Static string drawn once on line 1 (e.g. "Morse RX:").
        """
        self.lcd        = lcd
        self.font       = font
        self.last_drawn = None

        # Clear screen and draw the static label - never redrawn after this
        self.lcd.clear(bg_color)
        self.lcd.draw_text(text_x, line1_y, label, self.font, fg_color)

    def update(self, text):
        """
        Redraw line 2 with the last 20 characters of text.

        Skips all SPI activity if the visible content has not changed,
        minimising scanline artifacts on the slow ILI9341 refresh.

        Parameters
        ----------
        text : str
            The full morse string received so far; only the trailing
            display_chars characters are rendered.

        Returns
        -------
        None
        """
        # Take last 20 chars and pad with spaces to erase leftover glyphs
        snippet = text[-display_chars:]
        while len(snippet) < display_chars:
            snippet = snippet + " "

        # Dirty-check - skip redraw if nothing visible has changed
        if snippet == self.last_drawn:
            return
        self.last_drawn = snippet

        # Clear only the line 2 bounding box, then draw new text
        for row in range(text_h):
            self.lcd.draw_hline(text_x, line2_y + row, text_w, bg_color)
        self.lcd.draw_text(text_x, line2_y, snippet, self.font, fg_color)


class MorseReceiver:
    """
    Reads newline-terminated morse strings from a UART and forwards them
    to a DisplayDriver instance for rendering.

    Attributes
    ----------
    uart : UART
        The MicroPython UART object to read from.
    display : DisplayDriver
        The display instance that renders received messages.
    rx_buf : bytes
        Internal accumulation buffer for incoming UART bytes.
    morse_content : str
        The most recently received (non-empty) morse string.

    Methods
    -------
    poll():
        Read available UART bytes, extract complete lines, and update display.
    """

    def __init__(self, uart, display):
        """
        Bind a UART and a DisplayDriver together.

        Parameters
        ----------
        uart : UART
            Initialised MicroPython UART object (e.g. UART(1, 115200)).
        display : DisplayDriver
            Initialised DisplayDriver that will render received strings.
        """
        self.uart          = uart
        self.display       = display
        self.rx_buf        = b""
        self.morse_content = ""

    def poll(self):
        """
        Non-blocking UART poll - call repeatedly from the main loop.

        Appends any available bytes to the internal buffer, then extracts
        and processes every complete newline-terminated line. Silently
        discards lines that cannot be decoded as UTF-8 or are blank.

        Returns
        -------
        None
        """
        if not self.uart.any():
            return

        self.rx_buf += self.uart.read()

        # Process every complete line in the buffer
        while b"\n" in self.rx_buf:
            line, self.rx_buf = self.rx_buf.split(b"\n", 1)
            try:
                decoded = line.decode('utf-8').strip()
            except UnicodeError:
                continue        # drop malformed bytes

            if decoded:
                self.morse_content = decoded
                self.display.update(self.morse_content)


# Entry point <><><><><><><><><><><><><><><><><><><><><><><><>

display  = DisplayDriver(lcd, unispace, "Morse RX:")
receiver = MorseReceiver(UART(1, 115200), display)

# Brief boot confirmation on line 2, then clear it before live RX begins
display.update("LCD OK")
sleep(1)
display.update("")

# Main loop - poll UART continuously at 10 ms intervals
while True:
    receiver.poll()
    sleep(0.01)