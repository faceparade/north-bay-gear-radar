from audio_scraper.scoring import PricingEvidence, ScoreInputs, score_candidate


def test_foundational_interface_with_large_discount_scores_high():
    result = score_candidate(ScoreInputs(
        gap_fit=30, condition=12, compatibility=9, completeness=8,
        freshness_proximity=9, fun_factor=6, resale_safety=7,
        asking_price=25, pricing=PricingEvidence(used_low=74, used_high=118, confidence=.9),
    ))
    assert result.value_points >= 23
    assert result.total >= 90


def test_defect_and_legacy_driver_penalties_are_applied():
    result = score_candidate(ScoreInputs(
        gap_fit=10, condition=5, compatibility=4, completeness=8,
        freshness_proximity=8, fun_factor=10, resale_safety=5,
        asking_price=240, pricing=PricingEvidence(used_low=260, used_high=350, confidence=.8),
        risk_flags=("seller_disclosed_defect", "legacy_driver_risk"),
    ))
    assert result.penalty_points == 18
    assert result.total < 55


def test_unknown_price_evidence_does_not_fabricate_value_points():
    result = score_candidate(ScoreInputs(
        gap_fit=30, condition=10, compatibility=8, completeness=5,
        freshness_proximity=5, fun_factor=3, resale_safety=5,
        asking_price=None, pricing=PricingEvidence(confidence=0),
    ))
    assert result.value_points == 0
    assert "insufficient_price_evidence" in result.notes
