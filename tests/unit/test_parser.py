from src.web_scraper.parser import DetailParser, ListingParser


def test_parse_apartment_links():
    html = """
    <html>
      <body>
        <article data-name="CardComponent">
          <a class="_93444fe79c--link--eoxce" href="http://example.com/listing1"></a>
        </article>
        <article data-name="CardComponent">
          <a class="_93444fe79c--link--eoxce" href="http://example.com/listing2"></a>
        </article>
      </body>
    </html>
    """
    parser_instance = ListingParser(html)
    links = parser_instance.parse_apartment_links()
    assert links == ["http://example.com/listing1", "http://example.com/listing2"]


def test_parse_apartment_details_with_json_ld():
    html = """
    <html>
      <head>
        <script type="application/ld+json">
          {
            "@type": "Product",
            "name": "Test Apartment",
            "description": "Spacious apartment",
            "offers": {"price": "300000", "priceCurrency": "USD"},
            "image": ["http://example.com/image1", "http://example.com/image2"]
          }
        </script>
      </head>
      <body></body>
    </html>
    """
    parser_instance = DetailParser(html)
    details = parser_instance.parse_apartment_details()
    assert details["title"] == "Test Apartment"
    assert details["description"] == "Spacious apartment"
    assert details["price"] == "300000"
    assert details["images"] == ["http://example.com/image1", "http://example.com/image2"]


def test_parse_apartment_details_with_fallback():
    html = """
    <html>
      <body>
        <span data-mark="OfferTitle">Fallback Title</span>
        <span data-mark="MainPrice">12345</span>
        <div data-name="AddressContainer">
          <a>Address Line 1</a>
          <a>Address Line 2</a>
        </div>
      </body>
    </html>
    """
    parser_instance = DetailParser(html)
    details = parser_instance.parse_apartment_details()
    assert details["title"] == "Fallback Title"
    assert details["price"] == "12345"
    assert details["address"] == "Address Line 1, Address Line 2"


def test_parse_apartment_details_invalid_json_ld():
    html = """
    <html>
      <head>
        <script type="application/ld+json">
          INVALID JSON
        </script>
      </head>
      <body>
        <span data-mark="OfferTitle">Fallback Title</span>
      </body>
    </html>
    """
    parser_instance = DetailParser(html)
    details = parser_instance.parse_apartment_details()
    assert details["title"] == "Fallback Title"
