from app.databricks_client import _coalesce_content


def test_coalesce_handles_string():
    assert _coalesce_content("hello") == "hello"


def test_coalesce_handles_list_of_chunks():
    chunks = [
        {"type": "text", "text": "foo"},
        {"text": "bar"},
        {"content": "baz"},
        "!",
    ]
    assert _coalesce_content(chunks) == "foobarbaz!"


class _Chunk:
    def __init__(self, text):
        self.text = text


def test_coalesce_handles_objects_and_lists():
    chunks = [
        _Chunk("Hello "),
        {"text": ["world", "! "]},
        _Chunk(["Have", " ", "fun"]),
    ]
    assert _coalesce_content(chunks) == "Hello world! Have fun"
