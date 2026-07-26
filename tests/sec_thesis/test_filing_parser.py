from sec_thesis.filing_parser import extract_text

SAMPLE_HTML = """
<html>
  <head><style>body { color: red; }</style></head>
  <body>
    <script>var x = 1;</script>
    <h1>Item 1. Business</h1>
    <p>We compete with    Samsung Electronics
       and   Qualcomm    in various markets.</p>
  </body>
</html>
"""


def test_extract_text_strips_tags_and_scripts() -> None:
    text = extract_text(SAMPLE_HTML)

    assert "Item 1. Business" in text
    assert "compete with Samsung Electronics and Qualcomm" in text
    assert "var x = 1" not in text
    assert "color: red" not in text


def test_extract_text_collapses_whitespace() -> None:
    text = extract_text("<p>a   b\n\n c</p>")

    assert text == "a b c"


def test_extract_text_strips_hidden_inline_xbrl() -> None:
    html = """
    <html><body>
      <div style="display:none">
        <ix:header><ix:hidden>
          <ix:nonNumeric name="dei:AmendmentFlag">false</ix:nonNumeric>
        </ix:hidden></ix:header>
      </div>
      <p>Item 1. Business. We compete with Samsung Electronics.</p>
    </body></html>
    """

    text = extract_text(html)

    assert "AmendmentFlag" not in text
    assert "Item 1. Business" in text
