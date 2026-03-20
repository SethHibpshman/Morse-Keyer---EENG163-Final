# Iambic Morse Keyer & Trainer

<img src="https://raw.githubusercontent.com/SethHibpshman/Morse-Keyer---EENG163-Final/main/Main%20Picture.jpg" width="40%">

A standalone, feature-rich Morse code keyer and trainer built on the ESP32-S3 running MicroPython. Designed as a hands-on embedded systems project covering real-time signal generation, hardware input handling, OLED display, settings menus, multi-mode keying, automatic decoding, and inter-device communication.

---

## [Demo Video](https://youtu.be/7UfE0N1uJJo)

---

## Features

- **Four keying modes** — Iambic A, Iambic B, Ultimatic, and Straight Key
- **Real-time morse decoding** — automatically decodes keyed input to text on the OLED
- **Rotary encoder settings menu** — scroll and edit WPM, volume, LED, decoding toggle, and keying mode
- **Keyboard Replay Mode** — T9-style multi-tap keypad input encodes text to morse and plays it back
- **Automatic letter and word spacing** — gap detection scales with WPM setting
- **Sleep mode with screensaver** — bouncing logo after 60 seconds of inactivity
- **Boot screen** — typewriter-style startup sequence
- **Debug mode** — live paddle state, encoder pins, keypad input, and memory readout
- **UART communication** — transmits morse content to an STM32 relay display over serial

---

## Hardware

| Component | Details |
|---|---|
| Microcontroller | ESP32-S3 |
| Display | SSD1306 128x64 OLED (SoftI2C) |
| Paddles | 2x momentary buttons (Dit / Dah) |
| Keypad | 4x4 membrane matrix keypad |
| Rotary Encoder | CLK, DT, SW with long-press menu activation |
| Buzzer | Piezo PWM buzzer |
| LED | Single external indicator LED |
| Communication | UART1 to STM32 relay at 115200 baud |

---

## Pin Mapping

| Pin | Function |
|---|---|
| 7 | Dit paddle |
| 16 | Dah paddle |
| 38 | Buzzer (PWM) |
| 1 | External LED |
| 4 | Rotary CLK |
| 47 | Rotary DT |
| 45 | Rotary SW |
| 46 | OLED SCL |
| 8 | OLED SDA |
| 17 | UART TX |
| 18 | UART RX |
| 5, 6, 15, 17 | Keypad rows |
| 18, 2, 39, 40 | Keypad columns |

---

## PCB Design

Designed in KiCad. Project files available in [`/PCB Design - KiCad Program/ESP32 Board`](PCB%20Design%20-%20KiCad%20Program/ESP32%20Board).

<img src="https://raw.githubusercontent.com/SethHibpshman/Morse-Keyer---EENG163-Final/main/PCB%20Design%20-%20KiCad%20Program/ESP32%20Board/PCB Layout.png" width="30%">

---

## Software

Written entirely in **MicroPython**.

**Dependencies:**
- `ssd1306` — OLED driver
- `gfx` — OLED graphics primitives
- `keypad` — 4x4 matrix keypad driver
- `urandom` — screensaver randomization

---

## Project Structure

```
main.py          # Full application — hardware init, all functions, main loop
```

---

## Settings Menu

Hold the rotary encoder button for 2 seconds to open the settings menu. Short press to enter edit mode on a selected item. Rotate to scroll or adjust values.

| Setting | Options |
|---|---|
| Mode | Sandbox, Training, Keyboard Replay, Telegraph, Debug |
| Keying Mode | Iambic A, Iambic B, Ultimatic, Straight Key |
| Volume | 0 – 10 |
| LED | Enabled / Disabled |
| Decoding | Enabled / Disabled |
| About | Scrolling credits page |
| Reset | Hard resets the device |

---

## Keying Modes

| Mode | Behavior |
|---|---|
| **Iambic A** | Alternates dit/dah while both paddles held; stops on release |
| **Iambic B** | Same as A but sends one extra element after both paddles are released |
| **Ultimatic** | Last-pressed paddle wins when both are held simultaneously |
| **Straight Key** | Either paddle held produces a continuous tone |

---

## Morse Decoding

Gap detection runs automatically. After a paddle idle period equal to 3x the dit duration, a letter space is inserted and the last morse sequence is decoded. After 7x the dit duration, the space is upgraded to a word break. All thresholds scale with the live WPM setting.

---

## Keyboard Replay Mode

Enter text using the 4x4 keypad with T9-style multi-tap input (phone keyboard layout). The device encodes the typed text to morse in real time and displays it on the OLED. Press **B** to play the encoded sequence through the buzzer.

| Key | Control Action |
|---|---|
| A | Backspace |
| B | Play current text as morse |

---

## UART / STM32 Integration

In Telegraph mode, the device transmits the current morse string over UART1 as a UTF-8 newline-terminated message on each loop tick. A companion STM32 device running a separate display driver receives and renders the last 20 characters on an ILI9341 LCD.

---
## Cost

| Item | Qty | Unit | Total |
|---|---|---|---|
| ESP32-S3 Dev Board | 1 | $12.00 | $12.00 |
| Push Buttons (momentary) | 3 | $0.05 | $0.15 |
| Piezo Buzzer | 1 | $1.00 | $1.00 |
| LED | 1 | $0.03 | $0.03 |
| Resistors, wires, protoboard | — | — | $5.00 |
| SSD1306 OLED 128x64 | 1 | $3.00 | $3.00 |
| Rotary Encoder | 1 | $3.00 | $3.00 |
| 4x4 Membrane Keypad | 1 | $5.00 | $5.00 |
| PCBs (x3) | 3 | — | $15.00 |
| 3D-printed enclosure | 1 | — | $0.00 |
| STM32 Microcontroller | 1 | $10.00 | $10.00 |
| Aux ports / cables | — | — | $13.00 |
| 2nd ESP32 node (full duplicate) | — | — | $29.13 |
| Microphone / analog input | 1 | $3.00 | $3.00 |
| Misc analog sensors | 1 | $2.00 | $2.00 |
| **Hardware Total** | | | **$101.26** |
| Software | — | — | $0.00 |
| Tools | — | — | $0 – $30 |
| **Grand Total** | | | **~$101 – $131** |

> **Notes:**
> - Unit costs reflect bulk purchasing (50–100 units) — individual retail prices are significantly higher.
> - Salvaged or borrowed components are not included; actual cost may be lower.
> - 3D printing assumes university printer access. Outsourced printing would add to the total.
> - PCB cost assumes overseas fabrication. Any revision spins add another ~$15 per run.
> - The second ESP32 node (v4.0 network) requires a full hardware duplicate but does not include a second PCB.

---

## Author

**Seth Hibpshman**
Student of Electrical Engineering — Eastern Washington University
EENG 163: Introduction to Embedded Systems

---

## License

GNU General Public License v3.0
