from detection import count_sensitive_items, detect_sensitive_data


def test_detect_sensitive_data_expected_types():
    text = (
        "National ID 12345678, phone 0712345678, "
        "email person@example.org, KRA PIN A123456789B."
    )
    findings = detect_sensitive_data(text)

    assert len(findings["national_ids"]) == 1
    assert len(findings["phone_numbers"]) == 1
    assert len(findings["emails"]) == 1
    assert len(findings["kra_pins"]) == 1
    assert count_sensitive_items(findings) == 4
