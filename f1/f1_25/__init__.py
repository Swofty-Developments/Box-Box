"""
F1 25 — UDP format 2025.

Changes from 2024 that the parser reads: participant names cut to 32 chars with
4 RGB livery colours appended, tyreBlisters[4] inserted after brakesDamage[4] in
car damage, the C6 compound and reverse track layouts.
"""
from ..f1_24 import COMPOUNDS as F1_24_COMPOUNDS, TRACKS as F1_24_TRACKS
from ..formats import FORMATS, F1Format

TRACKS = {
  **F1_24_TRACKS,
  39: "Silverstone Reverse", 40: "Red Bull Ring Reverse", 41: "Zandvoort Reverse",
}

COMPOUNDS = {**F1_24_COMPOUNDS, 22: "C6"}

F1_25 = FORMATS.add("2025", F1Format(
  packet_format=2025,
  game="F1 25",
  participant_size=57,
  name_len=32,
  damage_size=46,
  damage_front_wing=28,
  tracks=TRACKS,
  compounds=COMPOUNDS,
))
