from detection import count_sensitive_items, detect_sensitive_data


def test_detect_sensitive_data_expected_types():
    text = (
        "Full Name: Jane Mwangi\n"
        "National ID 12345678\n"
        "Phone 0712345678\n"
        "Email person@example.org\n"
        "KRA PIN A123456789B\n"
        "Password: P@ss1234\n"
        "Salary: KES 120,000\n"
    )
    findings = detect_sensitive_data(text)

    assert len(findings["personal_names"]) == 1
    assert len(findings["national_ids"]) == 1
    assert len(findings["phone_numbers"]) == 1
    assert len(findings["emails"]) == 1
    assert len(findings["kra_pins"]) == 1
    assert len(findings["passwords"]) == 1
    assert len(findings["financial_info"]) == 1
    assert count_sensitive_items(findings) == 7