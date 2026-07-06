from k_commerce_agent.price_compare import _parse_danawa_offers, _parse_naver_offers


def test_parse_naver_offers_extracts_price_rows() -> None:
    html = """
    <script>
    {"productName":"삼다수 2L 12개","lowPrice":"11900","mallName":"네이버쇼핑","id":"12345"}
    {"productName":"백산수 2L 12개","lowPrice":"13900","mallName":"스마트스토어","id":"67890"}
    </script>
    """

    offers = _parse_naver_offers(html)

    assert offers[0].title == "삼다수 2L 12개"
    assert offers[0].price == 11900
    assert "naver:" in offers[0].source


def test_parse_danawa_offers_extracts_price_rows() -> None:
    html = """
    <a name="productName">삼다수 2L 12개</a>
    <strong class="price_num">11,900원</strong>
    <a name="productName">백산수 2L 12개</a>
    <strong class="price_num">13,900원</strong>
    """

    offers = _parse_danawa_offers(html)

    assert offers[0].title == "삼다수 2L 12개"
    assert offers[0].price == 11900
    assert offers[0].source == "danawa"
