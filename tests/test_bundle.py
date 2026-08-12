from audio_scraper.bundle import BundleCandidate, choose_bundles


def test_bundle_paths_prioritize_foundation_then_fun():
    items = [
        BundleCandidate("Interface", 25, 92, "audio_interface"),
        BundleCandidate("Monitor system", 225, 78, "studio_monitor_system"),
        BundleCandidate("Digitone", 400, 82, "standalone_synth"),
        BundleCandidate("Keyboard controller", 60, 20, "midi_controller"),
    ]
    bundles = choose_bundles(items, budgets=(100, 300, 500))
    assert bundles[100].names == ("Interface",)
    assert set(bundles[300].names) == {"Interface", "Monitor system"}
    assert "Keyboard controller" not in bundles[500].names
