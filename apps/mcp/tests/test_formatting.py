"""Rich text to plain text."""

from infinity_mcp.formatting import html_to_text


def test_paragraphs_and_lists():
    html = "<p>Préparer l'offre</p><ul><li>Prix</li><li><p>Délais</p></li></ul><p></p>"

    assert html_to_text(html) == "Préparer l'offre\n\n- Prix\n- Délais"


def test_empty():
    assert html_to_text(None) == ""
    assert html_to_text("<p></p>") == ""
