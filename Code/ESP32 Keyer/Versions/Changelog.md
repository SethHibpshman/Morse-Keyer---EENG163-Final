# Morse Keyer & Trainer — Changelog

**Project:** ESP32-S3 Morse Keyer & Trainer
**Course:** EENG 163 — Final Project
**Total Logged Hours:** 53+

---

## v1.13.1
- Enhanced wake procedures on rotary encoder rotation
- Cleaned up memory usage display in debug mode

---

## v1.12.0
- Sleep mode after 60 seconds of inactivity
- Bouncing logo screensaver during sleep
- Typewriter-style boot screen on startup

---

## v1.11.0
- Added Debug Mode with live paddle state, encoder pins, keypad input, memory usage, and clock display

---

## v1.10.6 `+14 hrs`
- Keypad hardware integration
- Complete code overhaul to support multiple modes
- Keyboard Replay Mode: alphabetic keypad input with live morse encoding preview
- Key B plays the encoded morse string out loud with live decoding

---

## v1.10.5
- Decoding toggle setting now wired into program behavior
- Moved Keying Mode under Behavior heading in settings menu

---

## v1.10.4
- Reset option in settings menu now functional

---

## v1.10.3
- Scrollable about/credits page added to settings menu

---

## v1.10.2
- Section headings added to settings menu

---

## v1.10.1
- All settings menu values now drive program behavior (index-agnostic)

---

## v1.10.0 `+7 hrs`
- Full settings menu integration: volume and all settings now control live behavior
- Reworked how list-type settings (modes, keying modes) are applied

---

## v1.9.3
- Settings menu fully functional

---

## v1.9.2
- Fixed button release detection, long-hold vs short-hold edge cases

---

## v1.9.1
- Basic settings menu integration

---

## v1.9.0 `+4 hrs`
- Removed standalone mode button and mode display from OLED in preparation for settings menu

---

## Intermediary `+6 hrs`
- Rotary encoder testing and integration
- Enclosure design and build

---

## v1.8.0
- Integrated GFX graphics library for OLED drawing primitives

---

## v1.7.0
- Added `draw_right_aligned()` — morse content renders from the right edge so gaps are visible as text scrolls left
- Decoder now prints decoded letters to the OLED display in addition to decoding internally
- Decoder is called automatically before letter and word spaces are written

---

## v1.6.1
- Implemented basic morse decoding function

---

## v1.6.0 `+3 hrs`
- WPM-based timing formula added
- WPM displayed on OLED

---

## v1.5.1
- Code cleaned and reorganized, redundant code removed

---

## v1.5.0
- Tracks button release time in addition to press time
- Inserts letter space or word space (`/`) depending on idle duration

---

## v1.4.0 `+4 hrs`
- `gap_checker()` implemented: detects gaps between morse elements and classifies them as letter or word breaks
- Fixed OLED flicker caused by calling draw function without current content
- Timing variable names updated for clarity

---

## v1.3.2 `+3 hrs`
- Migrated to 128×64px OLED — UI updated to match
- Morse alphabet dictionary added
- Inter-symbol gap timing variable added

---

## v1.3.0
- Implemented Ultimatic keying mode
- Button state tracking: records when each paddle was first pressed and whether it is currently held

---

## v1.2.0
- Mode switching implemented via indexed list
- Removed `Straight Paddle` mode
- Fixed bug in Straight Key mode causing constant beeping
- Implemented Iambic B mode

---

## v1.1.0 `+7 hrs`
- Added keying mode selection
- Display updates to reflect active mode

---

## v1.0.1
- Removed redundant `last_d` initialization

---

## v1.0.0 `+7 hrs`
- Major code reorganization — modular structure established

---

## v0.3.0
- LED support for visual feedback
- Display shows only the last 16 characters of the morse string, keeping RAM usage bounded
- Removed shell dot/dash printout

---

## v0.2.0
- Remembers the last element sent — both-paddles-held now alternates based on which was pressed first rather than always starting with dit

---

## v0.1.0 `+5 hrs`
- Basic dit and dah output depending on which paddle is pressed
- Both paddles held produces alternating dit-dah pattern
