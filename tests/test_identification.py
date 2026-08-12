from audio_scraper.identification import identify_listing
from audio_scraper.models import ListingDetail


def item(title, description=""):
    return ListingDetail("craigslist", title, "https://example.test", title, description=description)


def test_identifies_known_models_and_roles():
    assert identify_listing(item("Line 6 UX2 USB Audio Interface")).model == "Line 6 POD Studio UX2"
    assert identify_listing(item("Persons Eris 3.5 and Sub 8BT studio monitor system")).model == "PreSonus Eris 3.5 + Eris Sub 8BT"
    assert identify_listing(item("Elektron Digitone 8-Voice FM Synth")).role == "standalone_synth"


def test_flags_redundant_midi_controller_and_defective_tr8():
    controller = identify_listing(item("Impact LX49+ keyboard controller"))
    assert controller.role == "midi_controller"
    assert "redundant_controller" in controller.risk_flags
    tr8 = identify_listing(item("Roland AIRA TR-8 Drum Machine", "closed hi-hat decay control does not seem to be working; repaired slider"))
    assert "seller_disclosed_defect" in tr8.risk_flags


def test_ambiguous_bundle_is_not_treated_as_exact_interface():
    result = identify_listing(item("Apogee One Apogee Groove UA Canon Camera Mic", "Apogee One with cables"))
    assert result.model == "Apogee ONE (generation unspecified) bundle"
    assert result.confidence < 0.8
    assert "exact_revision_unknown" in result.risk_flags
