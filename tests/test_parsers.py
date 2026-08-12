from audio_scraper.parsers import parse_craigslist_results, parse_ebay_results


CRAIGSLIST_HTML = '''
<html><body>
<ol class="cl-static-search-results">
<li class="cl-static-search-result" title="Focusrite Scarlett 2i2">
<a href="https://sfbay.craigslist.org/nby/msg/d/test/1234567890.html"></a>
<div class="title">Focusrite Scarlett 2i2</div><div class="price">$80</div>
<div class="location">Novato</div></li>
</ol><a class="button next" href="?s=120">next</a>
</body></html>'''

EBAY_HTML = '''
<html><body><ul class="srp-results">
<li class="s-item"><a class="s-item__link" href="https://www.ebay.com/itm/335123456789?hash=x">
<div class="s-item__title"><span>PreSonus AudioBox USB 96</span></div></a>
<span class="s-item__price">$59.99</span><span class="s-item__location">from United States</span></li>
</ul><a class="pagination__next" href="/sch/i.html?_pgn=2">Next</a></body></html>'''


def test_craigslist_parser_extracts_listing_and_next_page():
    page = parse_craigslist_results(CRAIGSLIST_HTML, "https://sfbay.craigslist.org/")
    assert len(page.listings) == 1
    assert page.listings[0].listing_id == "1234567890"
    assert page.listings[0].price_text == "$80"
    assert page.has_next
    assert page.next_url.endswith("s=120")


def test_craigslist_parser_accepts_current_opaque_view_ids():
    html = '''<li class="cl-static-search-result" title="Soundcraft mixer">
    <a href="https://www.craigslist.org/view/d/el-sobrante-soundcraft-mixer/aqzdgbTQx6mX4P6qP4ViEb">
    <div class="title">Soundcraft mixer</div><div class="price">$600</div>
    <div class="location">san rafael</div></a></li>'''
    page = parse_craigslist_results(html, "https://www.craigslist.org/")
    assert len(page.listings) == 1
    assert page.listings[0].listing_id == "aqzdgbTQx6mX4P6qP4ViEb"


def test_parses_ebay_cards_and_canonicalizes_tracking_url():
    page = parse_ebay_results(EBAY_HTML, "https://www.ebay.com/sch/i.html")
    assert len(page.listings) == 1
    assert page.listings[0].listing_id == "335123456789"
    assert page.listings[0].url == "https://www.ebay.com/itm/335123456789"
    assert page.has_next is True
