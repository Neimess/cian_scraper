import pytest

from src.web_scraper.scraper import CianScraper

# @pytest.mark.slow
# @pytest.mark.asyncio
# async def test_fetch_listings(monkeypatch):
#     async def fake_fetch(self):
#         html = """
#         <html>
#           <body>
#             <article data-name="CardComponent">
#               <a class="_93444fe79c--link--eoxce" href="http://example.com/listing1"></a>
#             </article>
#           </body>
#         </html>
#         """
#         return (html, 200, {})

#     monkeypatch.setattr(Requester, "fetch", fake_fetch)
#     scraper_instance = CianScraper()
#     listings = await scraper_instance.fetch_listings()
#     assert listings == ["http://example.com/listing1"]


# @pytest.mark.asyncio
# async def test_fetch_listing_details_success(monkeypatch):
#     test_html = """
#     <html>
#       <head>
#         <script type="application/ld+json">
#           {
#             "@type": "Product",
#             "name": "Test Apt",
#             "description": "Nice apartment",
#             "offers": {"price": "200000", "priceCurrency": "USD"},
#             "image": ["http://example.com/img1", "http://example.com/img2"]
#           }
#         </script>
#       </head>
#       <body></body>
#     </html>
#     """

#     async def fake_fetch(self):
#         return (test_html, 200, {})

#     monkeypatch.setattr(Requester, "fetch", fake_fetch)
#     scraper_instance = CianScraper()
#     details = await scraper_instance.fetch_listing_details("http://example.com/listing1")
#     assert details is not None
#     assert details.get("title") == "Test Apt"
#     assert details.get("description") == "Nice apartment"
#     assert details.get("price") == "200000"
#     assert details.get("url") == "http://example.com/listing1"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_fetch_listing_details(monkeypatch):
    scraper_instance = CianScraper()
    details = await scraper_instance.fetch_listing_details("http://example.com/listing1")
    assert details is None


class DummySession:
    def __init__(self):
        self.added = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def flush(self):
        pass

    async def commit(self):
        pass

    def add(self, item):
        self.added.append(item)
