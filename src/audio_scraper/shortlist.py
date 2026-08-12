from __future__ import annotations

from collections.abc import Iterable

from .identification import IdentifiedListing


ROLE_PRIORITY = {
    "audio_interface": 0,
    "studio_monitor_system": 1,
    "powered_pa_speaker": 2,
    "usb_mixer": 3,
    "standalone_synth": 4,
    "sampler": 5,
    "drum_machine": 6,
    "arranger_keyboard": 7,
    "acoustic_instrument": 8,
    "midi_controller": 99,
    "other": 100,
}


def shortlist(items: Iterable[IdentifiedListing]) -> list[IdentifiedListing]:
    selected = [item for item in items if "redundant_controller" not in item.risk_flags and item.role != "other"]
    return sorted(selected, key=lambda item: (ROLE_PRIORITY.get(item.role, 100), -item.confidence, item.title.lower()))
