from audio_scraper.identification import IdentifiedListing
from audio_scraper.shortlist import shortlist


def identified(title, role, confidence=.9, flags=()):
    return IdentifiedListing(title, title, role, confidence, tuple(flags))


def test_shortlist_prioritizes_setup_gaps_and_removes_redundant_controllers():
    items = [
        identified("UX2", "audio_interface"),
        identified("Eris pair", "studio_monitor_system"),
        identified("Impact LX49", "midi_controller", flags=("redundant_controller",)),
        identified("Digitone", "standalone_synth"),
    ]
    selected = shortlist(items)
    assert [x.role for x in selected] == ["audio_interface", "studio_monitor_system", "standalone_synth"]
