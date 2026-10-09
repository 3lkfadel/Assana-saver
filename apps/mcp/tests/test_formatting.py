"""Rich text to plain text."""

from infinity_mcp.formatting import html_to_text, text_to_html


def test_paragraphs_and_lists():
    html = "<p>Préparer l'offre</p><ul><li>Prix</li><li><p>Délais</p></li></ul><p></p>"

    assert html_to_text(html) == "Préparer l'offre\n\n- Prix\n- Délais"


def test_round_trip_of_written_text():
    text = "Ligne 1\n\n- a\n- b"

    assert html_to_text(text_to_html(text)) == text


def test_empty():
    assert html_to_text(None) == ""
    assert html_to_text("<p></p>") == ""
