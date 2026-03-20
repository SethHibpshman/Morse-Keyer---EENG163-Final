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

menu_items = [
    "WPM",
    "Mode",
    "Volume",
    "LED",
    "Keying Mode",
    "Decoding",
    "Buzzer"
]

values = [
    10,                                     # WPM (10–40)
    ['Training', 'Sandbox'],                # MODE
    5,                                      # VOLUME (0–10)
    False,                                  # LED
    ['Iambic A', 'Iambic B', 'Ultimatic', 'Straight Key'],
    False,                                  # DECODING
    True                                    # BUZZER
]

selected = 0
scroll = 0

LINE_HEIGHT = 10
MAX_VISIBLE_LINES = 6

# ===============================
# CENTERED TEXT (USE EXACTLY)
# ===============================
def draw_centered(text, center_x, y):
    width = len(text) * 8
    x = center_x - (width // 2)
    oled.text(text, x, y)

# ===============================
# DRAW FILLED RECT
# ===============================
def fill_rect(x, y, w, h, color):
    for i in range(h):
        g.hline(x, y + i, w, color)

# ===============================
# VALUE STRING
# ===============================
def value_to_str(idx, val):
    if idx in [3, 5, 6]:  # LED, DECODING, BUZZER
        return "Enabled" if val else "Disabled"
    if isinstance(val, list):
        return val[0]
    return str(val)

# ===============================
# DRAW MENU
# ===============================
def draw_menu():
    oled.fill(0)

    # ---------- EDIT MODE ----------
    if mode == MODE_EDIT:
        name = menu_items[selected]
        val  = value_to_str(selected, values[selected])

        draw_centered(name, 64, 18)
        draw_centered(val, 64, 36)

        oled.show()
        return

    # ---------- MENU MODE ----------
    global scroll
    if selected < scroll:
        scroll = selected
    elif selected >= scroll + MAX_VISIBLE_LINES:
        scroll = selected - MAX_VISIBLE_LINES + 1

    for i in range(scroll, min(scroll + MAX_VISIBLE_LINES, len(menu_items))):
        y = (i - scroll) * LINE_HEIGHT

        if y + LINE_HEIGHT > 64:
            continue

        name = menu_items[i]

        if i == selected:
            fill_rect(0, y, 128, LINE_HEIGHT, 1)
            oled.text(name, 4, y + 1, 0)
        else:
            oled.text(name, 4, y + 1, 1)

    oled.show()

# ===============================
# ENCODER HANDLER
# ===============================
def handle_encoder(delta):
    global selected

    if mode == MODE_MENU:
        selected += delta
        selected = max(0, min(selected, len(menu_items) - 1))
        return

    val = values[selected]

    if selected == 0:  # WPM
        values[selected] = min(max(10, val + delta), 40)

    elif selected == 2:  # VOLUME
        values[selected] = min(max(0, val + delta), 10)

    elif selected in [3, 5, 6]:  # LED, DECODING, BUZZER
        if delta != 0:
            values[selected] = not val

    elif selected in [1, 4]:  # MODE, KEYING MODE
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

    if last_clk == 0 and current_clk == 1:
        if dt.value() == 0:
            handle_encoder(+1)
        else:
            handle_encoder(-1)
        draw_menu()

    last_clk = current_clk

    if sw.value() == 0:
        handle_button()
        draw_menu()
        time.sleep_ms(200)

    time.sleep_ms(1)
