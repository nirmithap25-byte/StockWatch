# read_pdf.py
import os
import sys

# Try to import pypdf or PyPDF2
try:
    import pypdf
    PDF_LIB = "pypdf"
except ImportError:
    try:
        import PyPDF2 as pypdf
        PDF_LIB = "PyPDF2"
    except ImportError:
        PDF_LIB = None

if not PDF_LIB:
    print("Error: Neither pypdf nor PyPDF2 is installed.")
    sys.exit(1)

pdf_path = "DocScanner 8 Jul 2026 2-46 pm.pdf"

if not os.path.exists(pdf_path):
    print(f"Error: File not found at {pdf_path}")
    sys.exit(1)

print(f"Reading PDF using {PDF_LIB}...")
reader = pypdf.PdfReader(pdf_path)
total_pages = len(reader.pages)
print(f"Total Pages: {total_pages}")

# Print first 5 pages text to inspect if it is searchable
for i in range(min(5, total_pages)):
    print(f"\n--- PAGE {i+1} ---")
    text = reader.pages[i].extract_text()
    if text:
        print(text[:1000]) # First 1000 characters
    else:
        print("[No text extracted - page might be scanned image]")
