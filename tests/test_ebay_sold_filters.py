from audio_scraper.ebay_sold import (
    comparable_variant,
    market_evidence,
    is_exact_sale_title,
    is_plausible_sale_price,
)


def test_mackie_filter_rejects_bags_and_cases_but_keeps_mixer():
    model = "Mackie ProFX10v3"
    assert not is_exact_sale_title(model, "Mackie ProFX10v3 Mixer Bag Carry Case")
    assert is_exact_sale_title(model, "Mackie ProFX10v3 10-Channel Professional Mixer")


def test_tr8_filter_rejects_adjacent_models():
    model = "Roland AIRA TR-8"
    assert not is_exact_sale_title(model, "Roland TR-08 Rhythm Composer")
    assert not is_exact_sale_title(model, "Roland TR-8S Rhythm Performer")
    assert is_exact_sale_title(model, "Roland AIRA TR-8 Drum Machine")


def test_digitone_filter_rejects_protectors_and_special_editions():
    model = "Elektron Digitone (original)"
    pattern = r"(?i)elektron.*digitone|digitone.*elektron"
    assert not is_exact_sale_title(
        model, "Elektron Digitakt / Digitone / Syntakt cover protector", pattern
    )
    assert not is_exact_sale_title(model, "Elektron Digitone E25 Remix Edition", pattern)
    assert is_exact_sale_title(model, "Elektron Digitone MK1 FM Synthesizer", pattern)


def test_implausibly_low_card_prices_are_rejected_not_corrected():
    assert not is_plausible_sale_price("Mackie ProFX10v3", 2.69)
    assert not is_plausible_sale_price("Casio CT-X700", 12.50)
    assert is_plausible_sale_price("Mackie ProFX10v3", 269.00)
    assert is_plausible_sale_price("Casio CT-X700", 125.00)
    assert is_plausible_sale_price("Casio CTK-1000", 20.00)


def test_presonus_combined_bundle_is_not_used_as_a_component_comparable():
    assert comparable_variant(
        "PreSonus Eris 3.5 + Eris Sub 8BT",
        "PreSonus Eris 3.5 Monitors + Eris Sub 8BT Bundle",
    ) is None
    assert comparable_variant(
        "PreSonus Eris 3.5 + Eris Sub 8BT", "PreSonus Eris Sub 8BT"
    ) == "Eris Sub 8BT"


def test_market_evidence_uses_central_range_and_combines_presonus_components():
    rows = [
        *({"model": "Mackie ProFX10v3", "variant": "Mackie ProFX10v3", "sold_price": price}
          for price in (100, 120, 140, 160, 180, 200)),
        *({"model": "PreSonus Eris 3.5 + Eris Sub 8BT", "variant": "Eris 3.5 pair", "sold_price": price}
          for price in (50, 60, 70, 80, 90, 100)),
        *({"model": "PreSonus Eris 3.5 + Eris Sub 8BT", "variant": "Eris Sub 8BT", "sold_price": price}
          for price in (130, 140, 150, 160, 170, 180)),
    ]
    evidence = market_evidence(rows)
    assert evidence["Mackie ProFX10v3"]["used_low"] == 120
    assert evidence["Mackie ProFX10v3"]["used_high"] == 180
    assert evidence["Mackie ProFX10v3"]["sample_size"] == 6
    assert evidence["PreSonus Eris 3.5 + Eris Sub 8BT"]["used_low"] == 200
    assert evidence["PreSonus Eris 3.5 + Eris Sub 8BT"]["used_high"] == 260
    assert evidence["PreSonus Eris 3.5 + Eris Sub 8BT"]["sample_size"] == 12
