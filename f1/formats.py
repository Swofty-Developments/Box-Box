"""
F1 UDP formats. Each f1_XX folder registers the per-car layouts and id tables of one game.
"""
from dataclasses import dataclass

from registry import Registry

FORMATS = Registry("F1 UDP format")


@dataclass(frozen=True)
class F1Format:
  packet_format: int  # m_packetFormat in the header, also the key in FORMATS
  game: str
  participant_size: int  # bytes per ParticipantData
  name_len: int  # m_name length inside ParticipantData
  damage_size: int  # bytes per CarDamageData
  damage_front_wing: int  # m_frontLeftWingDamage offset inside CarDamageData
  tracks: dict[int, str]
  compounds: dict[int, str]  # m_actualTyreCompound ids
