from machine import Pin, SoftI2C
import time
import ssd1306
import gfx

# ===============================
# ROTARY ENCODER
# ===============================
clk = Pin(4, Pin.IN, Pin.PULL_UP)
dt  = Pin(47, Pin.IN, Pin.PULL_UP)
sw  = Pin(45, Pin.IN, Pin.PULL_UP)

last_clk = clk.value()

# ===============================
# DISPLAY
# ===============================
i2c = SoftI2C(scl=Pin(46), sda=Pin(8))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
g = gfx.GFX(128, 64, oled.pixel)

# ===============================
# MENU STATE
# ===============================
MODE_MENU = 0
MODE_EDIT = 1
mode = MODE_MENU

menu_items = ["Volume", "Speed", "Brightness"]
values = [50, 20, 80]

selected = 0

LINE_HEIGHT = 12

# ===============================
# DRAW FILLED RECTANGLE (since gfx.rect() can't fill)
# ===============================
def fill_rect(x, y, w, h, color):
    for i in range(h):
        g.hline(x, y + i, w, color)

# ===============================
# DRAW MENU
# ===============================
def draw_menu():
    oled.fill(0)

    for i, name in enumerate(menu_items):
        y = i * LINE_HEIGHT

        if i == selected:
            # highlight bar (filled manually)
            fill_rect(0, y, 128, LINE_HEIGHT, 1)
            oled.text(name, 2, y + 2, 0)

            if mode == MODE_MENU:
                oled.text(">", 115, y + 2, 0)
            else:
                oled.text(str(values[i]), 90, y + 2, 0)
        else:
            oled.text(name, 2, y + 2, 1)

    oled.show()

# ===============================
# ENCODER HANDLER
# ===============================
def handle_encoder(delta):
    global selected, mode, values

    if mode == MODE_MENU:
        selected += delta
        if selected < 0:
            selected = 0
        if selected >= len(menu_items):
            selected = len(menu_items) - 1

    elif mode == MODE_EDIT:
        values[selected] += delta
        if values[selected] < 0:
            values[selected] = 0
        if values[selected] > 100:
            values[selected] = 100

# ===============================
# BUTTON HANDLER
# ===============================
def handle_button():
    global mode

    if mode == MODE_MENU:
        mode = MODE_EDIT
    else:
        mode = MODE_MENU

# ===============================
# INITIAL DRAW
# ===============================
draw_menu()

# ===============================
# MAIN LOOP
# ===============================
while True:
    current_clk = clk.value()

    # rotary turn detection
    if last_clk == 0 and current_clk == 1:
        if dt.value() == 0:
            handle_encoder(+1)
        else:
            handle_encoder(-1)
        draw_menu()

    last_clk = current_clk

    # button press
    if sw.value() == 0:
        handle_button()
        draw_menu()
        time.sleep_ms(200)  # debounce

    time.sleep_ms(1)
