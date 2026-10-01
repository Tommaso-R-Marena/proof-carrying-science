from scripts.adversarial_v06_hardening import campaign


def test_v06_hardening_campaign_has_no_false_accepts(tmp_path):
    result = campaign(tmp_path)
    assert result["attacks"] >= 12
    assert result["false_accepts"] == 0, result
