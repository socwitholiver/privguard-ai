import os
import pytest
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.file_loader import FileLoader

loader = FileLoader()


def test_txt_extraction():
    content = loader.load_file("data/test.txt")
    assert isinstance(content, str)
    assert len(content) > 0


def test_unsupported_file(tmp_path):
    fake_file = tmp_path / "test.xyz"
    fake_file.write_text("Some content")

    with pytest.raises(ValueError):
        loader.load_file(str(fake_file))



def test_missing_file():
    with pytest.raises(FileNotFoundError):
        loader.load_file("data/nonexistent.txt")


def test_empty_file(tmp_path):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("")
    with pytest.raises(ValueError):
        loader.load_file(str(empty_file))
