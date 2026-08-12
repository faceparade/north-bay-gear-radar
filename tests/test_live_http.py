from audio_scraper.http_collectors import HttpFetcher


class Response:
    status_code = 200
    text = "<html>ok</html>"
    url = "https://example.test/final"


class Client:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return Response()


def test_http_fetcher_is_get_only_and_returns_final_url():
    client = Client()
    fetcher = HttpFetcher(client=client)
    html, final_url = fetcher.get("https://example.test/start")
    assert html == "<html>ok</html>"
    assert final_url == "https://example.test/final"
    assert client.calls[0][0] == "https://example.test/start"
