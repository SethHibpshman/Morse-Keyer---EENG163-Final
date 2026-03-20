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

menu_items = ["WPM", "Mode", "Volume", "LED", "Keying Mode", "Decoding"]
values = [
    10,                                     # WPM
    ['Training', 'Sandbox'],                # MODE
    5,                                      # VOLUME
    False,                                  # LED_ON
    ['Iambic A', 'Iambic B', 'Ultimatic', 'Straight Key'],  # KEYING_MODE
    False                                   # DECODING
]

selected = 0
LINE_HEIGHT = 10
MAX_VISIBLE_LINES = 6
scroll = 0  # top line currently visible

# ===============================
# DRAW FILLED RECTANGLE
# ===============================
def fill_rect(x, y, w, h, color):
    for i in range(h):
        g.hline(x, y + i, w, color)

# ===============================
# DRAW MENU WITH FULL SCROLLING
# ===============================
def draw_menu():
    oled.fill(0)

    # adjust scroll so selected line is always fully visible
    global scroll
    if selected < scroll:
        scroll = selected
    elif selected >= scroll + MAX_VISIBLE_LINES:
        scroll = selected - MAX_VISIBLE_LINES + 1

    # draw visible items
    for i in range(scroll, min(scroll + MAX_VISIBLE_LINES, len(menu_items))):
        y = (i - scroll) * LINE_HEIGHT
        name = menu_items[i]
        val = values[i]

        # skip items that wouldn't fully fit
        if y + LINE_HEIGHT > 64:
            continue

        if i == selected:
            fill_rect(0, y, 128, LINE_HEIGHT, 1)
            oled.text(name, 2, y + 2, 0)

            if mode == MODE_MENU:
                oled.text(">", 115, y + 2, 0)
            else:
                if isinstance(val, list):
                    val = val[0]
                elif isinstance(val, bool):
                    val = "ON" if val else "OFF"
                oled.text(str(val), 90, y + 2, 0)
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
        val = values[selected]
        # numeric ranges
        if selected == 0:  # WPM
            val += delta
            val = min(max(10, val), 30)
            values[selected] = val
        elif selected == 2:  # VOLUME
            val += delta
            val = min(max(0, val), 10)
            values[selected] = val
        # toggle booleans
        elif selected in [3, 5]:  # LED_ON or DECODING
            if delta != 0:
                values[selected] = not val
        # cycle list options
        elif selected in [1, 4]:  # MODE or KEYING_MODE
            idx = val.index(val[0])
            idx = (idx + delta) % len(val)
            val.insert(0, val.pop(idx))
            values[selected] = val

# ===============================
# BUTTON HANDLER
# ===============================
def handle_button():
    global mode
    mode = MODE_EDIT if mode == MODE_MENU else MODE_MENU

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
