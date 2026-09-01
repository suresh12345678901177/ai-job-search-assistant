from jobseeker.llm_client import _extract_json


def test_extract_json_plain():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_markdown_fence():
    text = '```json\n{"a": 1}\n```'
    assert _extract_json(text) == {"a": 1}


def test_extract_json_with_surrounding_prose():
    text = 'Sure, here you go:\n{"a": 1}\nHope that helps!'
    assert _extract_json(text) == {"a": 1}


def test_extract_json_tolerates_raw_newline_in_string():
    # A local model sometimes emits a literal newline inside a string value
    # instead of escaping it as \n - strict JSON parsing rejects that.
    text = '{"about": "Paragraph one.\nParagraph two."}'
    result = _extract_json(text)
    assert "Paragraph one." in result["about"]
    assert "Paragraph two." in result["about"]
