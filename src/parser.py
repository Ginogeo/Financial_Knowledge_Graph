import re
import json
import os
import time
import requests

# Import unstructured at module level (slow first import due to emoji library)
try:
    from unstructured.partition.pdf import partition_pdf
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    partition_pdf = None


def normalize_id(raw: str) -> str:
    """Return a clean, uppercase section ID, e.g. 'ITEM 7A' or 'NOTE 20'."""
    return " ".join(raw.strip().upper().split())


def extract_with_pdfminer(pdf_path: str) -> list:
    """Fast extraction using pdfminer directly (5-15 seconds for 10-K)."""
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextContainer, LTFigure
    except ImportError:
        raise ImportError(
            "pdfminer.six not installed. Install with: pip install pdfminer.six"
        )

    print("Using pdfminer for fast extraction...")
    
    class SimpleElement:
        """Mock element to match unstructured's interface."""
        def __init__(self, text: str):
            self.text = text
        
        def __str__(self):
            return self.text
        
        def __repr__(self):
            return f"TextElement({self.text[:50]}...)"

    elements = []
    for page_layout in extract_pages(pdf_path):
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                text = element.get_text().strip()
                if text:
                    elements.append(SimpleElement(text))
            elif isinstance(element, LTFigure):
                # Handle nested text in figures/tables
                for item in element:
                    if isinstance(item, LTTextContainer):
                        text = item.get_text().strip()
                        if text:
                            elements.append(SimpleElement(text))
    
    return elements


def extract_with_unstructured(pdf_path: str, use_tables: bool = False, strategy: str = "fast") -> list:
    """
    Standard extraction using unstructured library (1-2 minutes for 10-K).
    
    Args:
        pdf_path: Path to PDF file
        use_tables: Extract tables as HTML
        strategy: "fast" (no OCR) or "hi_res" (with Tesseract OCR)
            Note: hi_res strategy requires Tesseract OCR to be installed
            Download from: https://github.com/UB-Mannheim/tesseract/wiki
    """
    if not UNSTRUCTURED_AVAILABLE:
        raise ImportError(
            "unstructured library not installed. Install with: pip install unstructured"
        )
    
    print(f"Using unstructured library for extraction with strategy='{strategy}'...")
    if strategy == "hi_res":
        print(f"  Note: Requires Tesseract OCR to be installed and in PATH")
    
    elements = partition_pdf(
        filename=pdf_path,
        strategy=strategy,
        infer_table_structure=use_tables,
        languages=["eng"]  # Language for OCR
    )
    return elements


def extract_with_mistral_ocr(pdf_path: str, api_key: str = None, pdf_url: str = None) -> list:
    """
    Extract text using Mistral OCR API.
    
    Args:
        pdf_path: Path to PDF file (used for local info, not uploaded)
        api_key: Mistral API key
        pdf_url: HTTPS URL where PDF is hosted (required - upload your PDF to a public URL first)
    """
    if not api_key:
        try:
            from config import MISTRAL_API_KEY
            api_key = MISTRAL_API_KEY
        except ImportError:
            raise ValueError(
                "Mistral API key not found. Please set MISTRAL_API_KEY in config.py "
                "or pass it as a parameter. Get your API key at: https://console.mistral.ai"
            )
    
    if not pdf_url:
        raise ValueError(
            "PDF URL is required for Mistral OCR. "
            "Upload your PDF to a public URL (e.g., Google Drive, Dropbox, GitHub) and provide the direct link. "
            "Example: https://arxiv.org/pdf/2201.04234.pdf"
        )
    
    print("Using Mistral OCR API for extraction...")
    print(f"Processing PDF from URL: {pdf_url}")
    
    try:
        from mistralai import Mistral
    except ImportError:
        raise ImportError("mistralai library not installed. Install with: pip install mistralai")
    
    client = Mistral(api_key=api_key)
    
    # Process with Mistral OCR using document_url
    print("Sending to Mistral OCR...")
    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": pdf_url
        },
        table_format="html",  # Preserve tables as HTML
    )
    
    print(f"OCR completed. Processing {len(ocr_response.pages)} pages...")
    
    # Parse response into elements
    class SimpleElement:
        def __init__(self, text: str):
            self.text = text
        def __str__(self):
            return self.text
        def __repr__(self):
            return f"TextElement({self.text[:50]}...)"
    
    elements = []
    
    # Process each page
    for page in ocr_response.pages:
        # Get markdown content from page
        markdown_text = page.markdown
        
        if not markdown_text:
            continue
            
        # Split into paragraphs (double newline separates paragraphs)
        paragraphs = [p.strip() for p in markdown_text.split('\n\n') if p.strip()]
        
        for para in paragraphs:
            elements.append(SimpleElement(para))
    
    print(f"Extracted {len(elements)} text elements from OCR")
    return elements


def extract_with_pdfplumber(pdf_path: str, extract_tables: bool = True) -> list:
    """
    Fast extraction using pdfplumber (seconds for 10-K, excellent table detection).
    
    Args:
        pdf_path: Path to PDF file
        extract_tables: Extract tables as structured data
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber not installed. Install with: pip install pdfplumber"
        )
    
    print("Using pdfplumber for fast extraction with table detection...")
    
    class Text:
        """Text element to match unstructured's interface."""
        def __init__(self, text: str):
            self.text = text
        
        def __str__(self):
            return self.text
        
        def __repr__(self):
            return f"Text({self.text[:50]}...)"
    
    class Table:
        """Table element to match unstructured's interface."""
        def __init__(self, text: str, html: str = None):
            self.text = text
            self.metadata = type('obj', (object,), {'text_as_html': html or text})()
        
        def __str__(self):
            return self.text
        
        def __repr__(self):
            return f"Table({self.text[:50]}...)"
    
    elements = []
    table_count = 0
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            try:
                # Extract tables first
                if extract_tables:
                    tables = page.extract_tables()
                    if tables:
                        print(f"  Page {page_num}: Found {len(tables)} table(s)")
                    for table in tables:
                        if table and len(table) > 0:
                            table_count += 1
                            # Convert table to tab-separated text and HTML
                            table_text = "\n".join(["\t".join([str(cell) if cell else "" for cell in row]) for row in table])
                            # Create simple HTML table
                            html_rows = []
                            for i, row in enumerate(table):
                                tag = "th" if i == 0 else "td"
                                cells = "".join([f"<{tag}>{cell if cell else ''}</{tag}>" for cell in row])
                                html_rows.append(f"<tr>{cells}</tr>")
                            table_html = f"<table>{''.join(html_rows)}</table>"
                            elements.append(Table(table_text, table_html))
                
                # Extract text (excluding areas covered by tables if we extracted tables)
                text = page.extract_text()
                if text:
                    # Split into lines (not paragraphs) to better detect section headings
                    # Group consecutive lines into blocks, but keep potential headings separate
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and len(line) > 5:  # Skip very short fragments
                            elements.append(Text(line))
            except Exception as e:
                print(f"  ⚠️  Page {page_num}: Error during extraction - {str(e)[:100]} (skipping page)")
                continue
    
    print(f"Extracted {len(elements)} elements ({table_count} tables, {len(elements) - table_count} text blocks)")
    return elements


def process_document(
    pdf_path: str, 
    output_path: str, 
    method: str = "pdfplumber",
    strategy: str = "fast",
    use_tables: bool = True,
    mistral_api_key: str = None,
    mistral_pdf_url: str = None
):
    """
    Parse a PDF into structured JSON sections.
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Path to save the parsed JSON
        method: "pdfminer", "pdfplumber", "unstructured", or "mistral_ocr"
        strategy: "fast" or "hi_res" (only for unstructured method)
            Note: hi_res requires Tesseract OCR installed
        use_tables: Extract tables (for pdfplumber and unstructured methods)
        mistral_api_key: API key for Mistral OCR (only for mistral_ocr method)
        mistral_pdf_url: Public HTTPS URL to PDF (required for mistral_ocr method)
    """
    print(f"Looking for PDF at: {pdf_path}")
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"Parsing document using [{method.upper()}] method...")
    
    # Choose extraction method
    if method == "pdfminer":
        elements = extract_with_pdfminer(pdf_path)
    elif method == "pdfplumber":
        elements = extract_with_pdfplumber(pdf_path, use_tables)
    elif method == "unstructured":
        elements = extract_with_unstructured(pdf_path, use_tables, strategy)
    elif method == "mistral_ocr":
        elements = extract_with_mistral_ocr(pdf_path, mistral_api_key, mistral_pdf_url)
    else:
        raise ValueError(f"Unknown method: {method}. Use 'pdfminer', 'pdfplumber', 'unstructured', or 'mistral_ocr'")
    
    print(f"Extracted {len(elements)} raw elements from PDF.")

    # ------------------------------------------------------------------ #
    # Regex patterns                                                       #
    # ------------------------------------------------------------------ #

    # Matches: Item 1, Item 1A, Item 1B, Item 9C, Item 10–16, Item X
    item_pattern = re.compile(
        r"^Item\s+(\d{1,2}[A-Z]?|X)\b[\.\:]?\s*", re.IGNORECASE
    )
    # Matches: Note 1, Note 20, Note 1A
    note_pattern = re.compile(
        r"^Note\s+(\d+[A-Z]?)\b[\.\:]?\s*", re.IGNORECASE
    )
    # Matches: Part I / II / III / IV  (used for metadata only, not a boundary)
    part_pattern = re.compile(
        r"^Part\s+(I{1,3}V?|IV)\b", re.IGNORECASE
    )
    # Comprehensive cross-reference extraction
    ref_pattern = re.compile(
        r"(?:see(?:\s+also)?|refer(?:red)?\s+to|described\s+in|"
        r"discussed\s+in|set\s+forth\s+in|pursuant\s+to|"
        r"contained\s+in|referenced\s+in|as\s+noted\s+in|"
        r"as\s+described\s+in)\s+"
        r"((?:Note|Item)\s+\d+[A-Z]?)",
        re.IGNORECASE,
    )

    # ------------------------------------------------------------------ #
    # State                                                                #
    # ------------------------------------------------------------------ #
    sections = []
    current_part: str | None = None
    section_map: dict = {}  # Maps section ID to its section dict for handling duplicates
    finalized_ids: set = set()  # Track which sections have been finalized

    current_section = {
        "id": "PREAMBLE",
        "text": "",
        "type": "Preamble",
        "part": None,
        "references": [],
        "has_tables": False,
        "element_count": 0,
    }
    section_map["PREAMBLE"] = current_section

    def finalize_section(sec: dict):
        """Trim text and append section if it has content and not already finalized."""
        if sec["id"] in finalized_ids:
            return  # Already finalized, skip
        sec["text"] = sec["text"].strip()
        if sec["text"]:
            sec["word_count"] = len(sec["text"].split())
            sections.append(sec)
            finalized_ids.add(sec["id"])

    # ------------------------------------------------------------------ #
    # Main loop                                                            #
    # ------------------------------------------------------------------ #
    for element in elements:
        text = str(element).strip()
        if not text:
            continue

        el_type = type(element).__name__
        item_match = item_pattern.match(text)
        note_match = note_pattern.match(text)
        part_match = part_pattern.match(text)

        # 1. Track Part headings (Part I / II / III / IV) — metadata only
        if part_match:
            current_part = normalize_id(
                part_match.group(0).strip()
            )
            # Fall through so the Part heading text is still appended below

        # 2. New Item or Note → save current section, open a new one (or switch to existing if duplicate)
        if item_match or note_match:
            if item_match:
                raw_id = "ITEM " + normalize_id(item_match.group(1))
            else:
                raw_id = "NOTE " + normalize_id(note_match.group(1))
            
            normalized_id = normalize_id(raw_id)
            
            # Check if this is a duplicate (likely from table of contents or index pages)
            if normalized_id in section_map:
                # Switch current_section to the original section to append content there
                current_section = section_map[normalized_id]
                continue  # Skip the duplicate heading text itself
            
            # New section: finalize previous and create new
            finalize_section(current_section)

            current_section = {
                "id": normalized_id,
                "text": text + "\n",
                "type": "Section",
                "part": current_part,
                "references": [],
                "has_tables": False,
                "element_count": 1,
            }
            section_map[normalized_id] = current_section
            continue

        # 3. Extract cross-references from body text
        for ref_match in ref_pattern.finditer(text):
            target = normalize_id(ref_match.group(1))
            if target not in current_section["references"]:
                current_section["references"].append(target)

        # 4. Append content (handle tables vs plain text)
        if el_type == "Table":
            current_section["has_tables"] = True
            html = getattr(
                getattr(element, "metadata", None), "text_as_html", None
            )
            block = html if html else text
            current_section["text"] += f"\n[TABLE]\n{block}\n[/TABLE]\n"
        else:
            # All text elements (SimpleElement, Text, or unstructured elements)
            current_section["text"] += f"{text}\n"

        current_section["element_count"] += 1

    finalize_section(current_section)  # flush the last section

    # ------------------------------------------------------------------ #
    # Write output                                                         #
    # ------------------------------------------------------------------ #
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sections, f, indent=4, ensure_ascii=False)

    _print_summary(sections, output_path)


def _print_summary(sections: list, output_path: str):
    total_words = sum(s.get("word_count", 0) for s in sections)
    with_refs   = [s for s in sections if s["references"]]
    with_tables = [s for s in sections if s["has_tables"]]

    print(f"\nSaved {len(sections)} sections to: {output_path}")
    print(f"  Total words        : {total_words:,}")
    print(f"  Sections with refs : {len(with_refs)}")
    print(f"  Sections w/ tables : {len(with_tables)}")
    print("\n  Sections found:")
    for s in sections:
        part  = s["part"] or "—"
        refs  = f"  → {s['references']}" if s["references"] else ""
        print(f"    [{part:8}] {s['id']}{refs}")


if __name__ == "__main__":
    BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf_path    = os.path.join(BASE_DIR, "data", "raw", "SEC 10-K Filing.pdf")
    output_path = os.path.join(BASE_DIR, "data", "processed", "parsed_data1.json")


    # ===================================================================
    # 🚀 CHOOSE PARSING METHOD:
    # 
    # "pdfminer"     → Fastest (5-15 seconds) - No tables, text only
    # "pdfplumber"   → Fast with excellent table detection (10-30 seconds) ⭐ RECOMMENDED for 10-Ks
    #                  Best for SEC filings with embedded text and tables
    # "unstructured" → Slower but powerful layout analysis (1-2 minutes)
    #                  strategy="fast" - No OCR needed
    #                  strategy="hi_res" - Uses Tesseract OCR for layout detection
    #                    Requires: Tesseract OCR installed and in PATH
    #                    Download: https://github.com/UB-Mannheim/tesseract/wiki
    # "mistral_ocr"  → Mistral AI OCR - Free tier, supports tables (30-60 seconds)
    #                  Requires: Upload PDF to public URL and set mistral_pdf_url below
    # ===================================================================
    
    # For mistral_ocr: Upload your PDF to a public URL and paste it here
    mistral_pdf_url = "https://www.sec.gov/Archives/edgar/data/320193/000032019326000006/aapl-20251227.htm"  # UPDATE THIS!
    
    process_document(
        pdf_path=pdf_path,
        output_path=output_path,
        method="pdfplumber",         # ⭐ Recommended for 10-Ks
        use_tables=True,             # Extract tables
        mistral_pdf_url=mistral_pdf_url,
          # Required for mistral_ocr method
    )
