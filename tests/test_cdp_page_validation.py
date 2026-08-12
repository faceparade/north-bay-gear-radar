from audio_scraper.cdp_browser import validate_search_page


def test_validate_search_page_accepts_expected_marketplace_page():
    validate_search_page(
        source="facebook",
        url="https://www.facebook.com/marketplace/search/?query=Digitone",
        title="Facebook Marketplace",
        has_login_form=False,
    )


def test_validate_search_page_rejects_sign_in_redirect():
    try:
        validate_search_page(
            source="ebay",
            url="https://signin.ebay.com/ws/eBayISAPI.dll?SignIn",
            title="Sign in or Register | eBay",
            has_login_form=True,
        )
    except RuntimeError as exc:
        assert "authentication" in str(exc).lower()
    else:
        raise AssertionError("sign-in redirect should fail the search")
