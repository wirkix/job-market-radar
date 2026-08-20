from scraper.clean import (
    extract_headquarters,
    is_data_role_candidate,
    merge_posting,
    normalize_whitespace,
    parse_about_list,
    parse_pubdate,
    posting_id_from_url,
    split_title,
    strip_html,
)


def test_split_title_normal_case():
    company, title = split_title("Stripe: Head of Self-Serve Paid Media")
    assert company == "Stripe"
    assert title == "Head of Self-Serve Paid Media"


def test_split_title_no_colon_falls_back_to_whole_string():
    company, title = split_title("Just A Job Title With No Company")
    assert company is None
    assert title == "Just A Job Title With No Company"


def test_posting_id_from_url_uses_final_slug():
    url = "https://weworkremotely.com/remote-jobs/stripe-head-of-self-serve-paid-media"
    assert posting_id_from_url(url) == "stripe-head-of-self-serve-paid-media"


def test_posting_id_from_url_ignores_trailing_slash():
    assert posting_id_from_url("https://weworkremotely.com/remote-jobs/foo/") == "foo"


def test_strip_html_collapses_tags_and_whitespace():
    html = "<p>Hello   <strong>World</strong></p>\n<ul><li>one</li><li>two</li></ul>"
    assert strip_html(html) == "Hello World one two"


def test_strip_html_none_input():
    assert strip_html(None) is None


def test_normalize_whitespace_collapses_and_trims():
    assert normalize_whitespace("  a\n\t b   c  ") == "a b c"
    assert normalize_whitespace("   ") is None
    assert normalize_whitespace(None) is None


def test_parse_about_list_extracts_known_labels():
    items = [
        "Posted on 29 days ago",
        "Apply before Aug 21th, 2026",
        "Job type Full-Time",
        "Category Full-Stack Programming",
        "Region Anywhere in the World",
    ]
    parsed = parse_about_list(items)
    assert parsed["posted_on_relative"] == "29 days ago"
    assert parsed["apply_before"] == "Aug 21th, 2026"
    assert parsed["job_type"] == "Full-Time"
    assert parsed["category"] == "Full-Stack Programming"
    assert parsed["region"] == "Anywhere in the World"
    assert parsed["salary"] is None


def test_parse_pubdate_valid_rfc822():
    dt = parse_pubdate("Wed, 22 Jul 2026 07:03:14 +0000")
    assert dt is not None
    assert dt.year == 2026 and dt.month == 7 and dt.day == 22


def test_parse_pubdate_invalid_returns_none():
    assert parse_pubdate("not a date") is None
    assert parse_pubdate(None) is None


def test_is_data_role_candidate_matches_keyword():
    assert is_data_role_candidate("Senior Data Engineer", "Build pipelines in Airflow")
    assert is_data_role_candidate("Analytics Engineer", None)
    assert not is_data_role_candidate("Head of Paid Media", "Manage ad budgets across channels")


def test_extract_headquarters_finds_labelled_first_paragraph():
    html = (
        "<p><strong>Headquarters:</strong> San Francisco, New York, Remote in the US</p>"
        "<h2>Who we are</h2><p>Stripe is a financial infrastructure platform.</p>"
    )
    assert extract_headquarters(html) == "San Francisco, New York, Remote in the US"


def test_extract_headquarters_returns_none_when_first_block_is_unrelated():
    html = "<p>This posting opens with something else entirely.</p>"
    assert extract_headquarters(html) is None


def test_extract_headquarters_none_input():
    assert extract_headquarters(None) is None


def test_extract_headquarters_trims_trailing_url():
    html = "<p>Headquarters: Minneapolis, MN URL: http://collaboration.ai</p>"
    assert extract_headquarters(html) == "Minneapolis, MN"


def test_merge_posting_combines_rss_and_detail():
    rss_item = {
        "posting_id": "acme-data-engineer",
        "source": "weworkremotely",
        "source_category": "remote-back-end-programming-jobs",
        "title_raw": "Acme Corp: Senior Data Engineer",
        "region": "Anywhere in the World",
        "category": "Back-End Programming",
        "description_html": "<p>Headquarters: Berlin, Germany</p><p>We use Airflow and dbt.</p>",
        "pubdate_raw": "Wed, 22 Jul 2026 07:03:14 +0000",
        "apply_url": "https://weworkremotely.com/remote-jobs/acme-data-engineer",
    }
    detail = {
        "job_title": "Senior Data Engineer",
        "company_name": "Acme Corp",
        "about": {
            "posted_on_relative": "1 day ago",
            "apply_before": "Aug 1st, 2026",
            "job_type": "Full-Time",
            "category": "Back-End Programming",
            "region": "Anywhere in the World",
            "salary": "$120,000 or more USD",
        },
    }

    row = merge_posting(rss_item, detail)

    assert row["posting_id"] == "acme-data-engineer"
    assert row["company_name"] == "Acme Corp"
    assert row["job_title"] == "Senior Data Engineer"
    assert row["company_headquarters"] == "Berlin, Germany"
    assert row["job_type"] == "Full-Time"
    assert row["salary_text"] == "$120,000 or more USD"
    assert row["is_data_role_keyword_match"] is True
    assert row["posted_at"].year == 2026


def test_merge_posting_without_detail_falls_back_to_rss_title():
    rss_item = {
        "posting_id": "solo-founder-hunt",
        "source": "weworkremotely",
        "source_category": "all-other-remote-jobs",
        "title_raw": "Beta Inc: Marketing Manager",
        "region": None,
        "category": None,
        "description_html": "<p>No data tools mentioned here.</p>",
        "pubdate_raw": None,
        "apply_url": "https://weworkremotely.com/remote-jobs/solo-founder-hunt",
    }
    row = merge_posting(rss_item, None)
    assert row["company_name"] == "Beta Inc"
    assert row["job_title"] == "Marketing Manager"
    assert row["is_data_role_keyword_match"] is False
    assert row["posted_at"] is None
