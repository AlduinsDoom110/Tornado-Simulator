# Tornado Simulator

An atmospheric tornado visualization built with Pygame featuring smooth EF-level transitions,
dense particle effects, and cinematic lighting.

## Features
- Swirling particle-based funnel with volumetric glow
- Animated stratified storm clouds and rolling ground fog
- Toggle between Enhanced Fujita scale levels (EF0–EF5) with spacebar or number keys
- Dynamic debris field intensity that scales with storm strength

## Requirements
Install dependencies with:

```bash
pip install -r requirements.txt
```

## Usage
Run the simulator with:

```bash
python tornado_simulator.py
```

Controls:
- `SPACE` or `ENTER`: cycle to the next EF level
- Number keys `0`–`5`: jump directly to a specific EF intensity
- `ESC`: exit the simulator
