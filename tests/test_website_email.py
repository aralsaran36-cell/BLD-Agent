from app.lead_evaluation.website import extract_emails, is_directory, decode_cfemail


def test_mailto_link():
    html = '<a href="mailto:Info@Clinic.com?subject=hi">mail</a>'
    assert extract_emails(html) == ["info@clinic.com"]


def test_obfuscated_at_dot():
    html = "<p>Write to care [at] clinic (dot) in</p>"
    assert extract_emails(html) == ["care@clinic.in"]


def test_cloudflare_cfemail():
    key = 0x42
    plain = "a@b.com"
    hexstr = f"{key:02x}" + "".join(f"{ord(c) ^ key:02x}" for c in plain)
    assert decode_cfemail(hexstr) == plain
    html = f'<span data-cfemail="{hexstr}">[protected]</span>'
    assert extract_emails(html) == ["a@b.com"]


def test_json_ld_email():
    html = '<script type="application/ld+json">{"@type":"Hospital","email":"hello@h.org"}</script>'
    assert extract_emails(html) == ["hello@h.org"]


def test_junk_filtered():
    assert extract_emails("<p>logo@2x.png example@example.com</p>") == []


def test_directory_blocklist():
    assert is_directory("https://www.dialmia.com/kurinji-siddha")
    assert is_directory("https://m.facebook.com/clinic")
    assert not is_directory("https://www.kurinjiclinic.in")