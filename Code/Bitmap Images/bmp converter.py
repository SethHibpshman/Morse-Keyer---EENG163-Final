import cv2

# 1. Load your image as grayscale
img = cv2.imread("logo.png", cv2.IMREAD_GRAYSCALE)
if img is None:
    raise FileNotFoundError("Image not found, check path")

# 2. Width and Height
oled_width = 32
oled_height = 32
img = cv2.resize(img, (oled_width, oled_height))

# 3. Convert to binary
_, bw_img = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)

# 4. Convert to bitmap array (list of bytes)
bitmap = []
for y in range(0, oled_height, 8):   # SSD1306 uses 8-pixel vertical pages
    for x in range(oled_width):
        byte = 0
        for bit in range(8):
            if y + bit < oled_height:
                pixel = bw_img[y + bit, x]
                if pixel > 0:  # white pixel
                    byte |= (1 << bit)
        bitmap.append(byte)

# 5. Print array as MicroPython-ready
print("oled_bitmap = [")
for i, b in enumerate(bitmap):
    end = "," if i < len(bitmap) - 1 else ""
    print(f"0x{b:02X}{end}", end="\n" if (i + 1) % 16 == 0 else " ")
print("]")