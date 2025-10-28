from pathlib import Path
from api.ingestion.extractors import extract_text, split_text


def test_extract_txt(tmp_path: Path):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    out = extract_text(p)
    assert "hello world" in out


def test_extract_docx(tmp_path: Path):
    # creiamo un docx minimale via python-docx
    from docx import Document as DocxDocument

    doc_path = tmp_path / "a.docx"
    d = DocxDocument()
    d.add_paragraph("ciao docx")
    d.save(str(doc_path))

    out = extract_text(doc_path)
    assert "ciao docx" in out


essential_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n2 0 obj\n<< /Type /Pages /Count 1 /Kids [3 0 R] >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 72 712 Td (hello pdf) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000103 00000 n \n0000000190 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n280\n%%EOF\n"


def test_extract_pdf(tmp_path: Path):
    from pypdf import PdfWriter

    pdf_path = tmp_path / "a.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with open(pdf_path, "wb") as f:
        writer.write(f)

    out = extract_text(pdf_path)
    assert isinstance(out, str)


def test_split_text_basic():
    text = "a" * 1500
    chunks = split_text(text, chunk_size=1000, chunk_overlap=200)
    assert len(chunks) >= 2
    assert all(isinstance(c, str) and len(c) > 0 for c in chunks)
