from __future__ import annotations

from dataclasses import dataclass
import re

from .models import ListingDetail


@dataclass(frozen=True, slots=True)
class IdentifiedListing:
    title: str
    model: str
    role: str
    confidence: float
    risk_flags: tuple[str, ...] = ()


KNOWN: list[tuple[re.Pattern, str, str, float]] = [
    (re.compile(r"\bline 6 (?:pod studio )?ux2\b", re.I), "Line 6 POD Studio UX2", "audio_interface", .96),
    (re.compile(r"\bapogee one\b", re.I), "Apogee ONE (generation unspecified) bundle", "audio_interface", .68),
    (re.compile(r"\b(?:persons|presonus) eris 3\.5.*sub 8bt\b", re.I), "PreSonus Eris 3.5 + Eris Sub 8BT", "studio_monitor_system", .92),
    (re.compile(r"\brockville.*rpg12\b", re.I), "Rockville RPG12", "powered_pa_speaker", .96),
    (re.compile(r"\bmackie profx10v3\b", re.I), "Mackie ProFX10v3", "usb_mixer", .98),
    (re.compile(r"\belektron digitone\b", re.I), "Elektron Digitone (original)", "standalone_synth", .92),
    (re.compile(r"\broland aira tr-?8\b", re.I), "Roland AIRA TR-8", "drum_machine", .98),
    (re.compile(r"\broland ms-?1 sampler\b", re.I), "Roland MS-1 Sampler", "sampler", .98),
    (re.compile(r"\bcasio ct-x700\b", re.I), "Casio CT-X700", "arranger_keyboard", .98),
    (re.compile(r"\bcasio ctk-1000\b", re.I), "Casio CTK-1000", "arranger_keyboard", .98),
    (re.compile(r"\b(?:impact lx49\+?|m-audio oxygen|keylab|komplete m32)\b", re.I), "MIDI keyboard controller", "midi_controller", .9),
    (re.compile(r"\bmicro ?monsta\b", re.I), "AudioThingies MicroMonsta 1", "standalone_synth", .95),
    (re.compile(r"\bmakala.*mk-te\b", re.I), "Makala MK-TE", "acoustic_instrument", .96),
]


def identify_listing(detail: ListingDetail) -> IdentifiedListing:
    haystack = f"{detail.title}\n{detail.description}"
    model, role, confidence = detail.title, "other", .4
    flags: list[str] = []
    for pattern, found_model, found_role, found_confidence in KNOWN:
        if pattern.search(haystack):
            model, role, confidence = found_model, found_role, found_confidence
            break
    if role == "midi_controller":
        flags.append("redundant_controller")
    if model.startswith("Apogee ONE"):
        flags.append("exact_revision_unknown")
    if re.search(r"\b(?:does not (?:seem to )?work|not working|broken|repaired|missing|no case)\b", detail.description, re.I):
        flags.append("seller_disclosed_defect")
    if role == "audio_interface" and model == "Line 6 POD Studio UX2":
        flags.append("legacy_driver_risk")
    if role == "studio_monitor_system" and not re.search(r"\b(?:pair|each speaker|speakers|monitors)\b", haystack, re.I):
        flags.append("pair_not_confirmed")
    return IdentifiedListing(detail.title, model, role, confidence, tuple(dict.fromkeys(flags)))
