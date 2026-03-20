from machine import Pin, SoftI2C
import time
import ssd1306
import gfx

# <><><><><><><><><><><><><><><><><><><><><><>
# HARDWARE SETUP (matches your project)
# <><><><><><><><><><><><><><><><><><><><><><>

# Rotary encoder
clk = Pin(4, Pin.IN, Pin.PULL_UP)
dt  = Pin(47, Pin.IN, Pin.PULL_UP)

last_clk = clk.value()

# OLED
i2c = SoftI2C(scl=Pin(46), sda=Pin(8))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
oled_gfx = gfx.GFX(128, 64, oled.pixel)

# <><><><><><><><><><><><><><><><><><><><><><>
# MENU DATA
# <><><><><><><><><><><><><><><><><><><><><><>

menu_items = [
    "Iambic A",
    "Iambic B",
    "Ultimatic",
    "Straight Key",
    "Settings",
    "About",
    "Debug",
    "Reset",
]

TOTAL_LINES = 6
LINE_HEIGHT = 10

highlight = 0     # 0–5 (visible selection)
shift = 0         # scroll offset into menu_items

# <><><><><><><><><><><><><><><><><><><><><><>
# DRAW MENU (gfx-based highlight)
# <><><><><><><><><><><><><><><><><><><><><><>

def draw_menu():
    oled.fill(0)

    visible_items = menu_items[shift : shift + TOTAL_LINES]

    for i, text in enumerate(visible_items):
        y = i * LINE_HEIGHT

        if i == highlight:
            # Highlight bar
            oled_gfx.fill_rect(0, y, 128, LINE_HEIGHT, 1)
            oled.text(">", 0, y, 0)
            oled.text(text, 10, y, 0)
        else:
            oled.text(text, 10, y, 1)

    oled.show()

# <><><><><><><><><><><><><><><><><><><><><><>
# INITIAL DRAW
# <><><><><><><><><><><><><><><><><><><><><><>

draw_menu()

# <><><><><><><><><><><><><><><><><><><><><><>
# MAIN LOOP
# <><><><><><><><><><><><><><><><><><><><><><>

while True:
    current_clk = clk.value()
    current_dt = dt.value()

    # Rising edge on CLK
    if last_clk == 0 and current_clk == 1:

        # Clockwise (DOWN)
        if current_dt == 0:
            if highlight < TOTAL_LINES - 1 and (highlight + shift) < len(menu_items) - 1:
                highlight += 1
            elif shift + TOTAL_LINES < len(menu_items):
                shift += 1

        # Counter-clockwise (UP)
        else:
            if highlight > 0:
                highlight -= 1
            elif shift > 0:
                shift -= 1

        draw_menu()

        # Debug output
        selected_index = highlight + shift
        print("Selected:", menu_items[selected_index])

    last_clk = current_clk
    time.sleep_ms(1)
