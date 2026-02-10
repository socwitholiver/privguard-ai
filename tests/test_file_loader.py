import sys
import os

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.file_loader import FileLoader

if __name__ == "__main__":
    loader = FileLoader()

    test_files = [
        "data/test.pdf",
        "data/test.docx",
        "data/test.txt",
    ]

    for file in test_files:
        print(f"\nTesting: {file}")
        try:
            content = loader.load_file(file)
            print("Extraction successful.")
            print("Preview:", content[:200])
        except Exception as e:
            print("Error:", e)
