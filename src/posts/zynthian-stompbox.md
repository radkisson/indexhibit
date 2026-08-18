---
title: Zynthian Stompbox — Neural Multi-FX Floor Unit
date: 2026-08-12
type: exhibit
tags: [hardware, instrument-design, guitar]
images: []
draft: false
---

## About

A custom guitar multi-FX floor unit: ZynthianOS on a Raspberry Pi 5 hosting NAM (Neural Amp Modeler) plus reverbs, delays, modulation. Five-inch touchscreen, four rotary encoders, eight footswitches in a 2×4 grid. Research complete, paused August 2026 awaiting parts.

## The interesting engineering

Tier 2 strategy: reuse Zynthian's Control PACK v5 (the hard PCB) but skip the MainBoard by replicating its two essential functions — the WS2812 3.3→5 V level shifter and the I2C pull-ups — on a ~$2 breakout. Verified against the actual KiCad netlists, not the marketing page (the MainBoard is not a passive wiring hub; it carries the 74LVC3G17 buffer, pull-ups, and RTC).

Footswitches: Zynthian V5 has no raw-GPIO footswitch path, so eight switches run through an RP2040 USB-MIDI controller into MIDI-learn. Guitar input: Arturia MiniFuse 1 (1 MΩ Hi-Z) — the MainBoard's 20 kΩ line input cannot serve a passive guitar. Power: 9 V pedal PSU → 5 V/5 A buck → Pi header.

## Bill of materials

≈ $500–550 all-in, every line verified or marked estimate.

Related: [[diy-space-as-instrument]].
