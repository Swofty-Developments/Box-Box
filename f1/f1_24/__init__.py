"""
F1 24 — UDP format 2024.
"""
from ..formats import FORMATS, F1Format

TRACKS = {
  0: "Melbourne", 1: "Paul Ricard", 2: "Shanghai", 3: "Bahrain",
  4: "Catalunya", 5: "Monaco", 6: "Montreal", 7: "Silverstone",
  8: "Hockenheim", 9: "Hungaroring", 10: "Spa", 11: "Monza",
  12: "Singapore", 13: "Suzuka", 14: "Abu Dhabi", 15: "Austin",
  16: "Interlagos", 17: "Red Bull Ring", 19: "Mexico City", 20: "Baku",
  26: "Zandvoort", 27: "Imola", 29: "Jeddah", 30: "Miami",
  31: "Las Vegas", 32: "Losail",
}

COMPOUNDS = {
  7: "INTER", 8: "WET",
  9: "DRY", 10: "WET",
  11: "SS", 12: "S", 13: "M", 14: "H", 15: "WET",
  16: "C5", 17: "C4", 18: "C3", 19: "C2", 20: "C1", 21: "C0",
  0: "C0", 1: "C1", 2: "C2", 3: "C3", 4: "C4", 5: "C5",
  6: "SOFT",
}

F1_24 = FORMATS.add("2024", F1Format(
  packet_format=2024,
  game="F1 24",
  participant_size=60,
  name_len=48,
  damage_size=42,
  damage_front_wing=24,  # after tyresWear[4] floats, tyresDamage[4], brakesDamage[4]
  tracks=TRACKS,
  compounds=COMPOUNDS,
))
