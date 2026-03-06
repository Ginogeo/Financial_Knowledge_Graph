"""Debug script to see what pdfplumber extracts from the PDF"""
import os
import re
from src.parser import extract_with_pdfplumber

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
pdf_path = os.path.join(BASE_DIR, "data", "raw", "SEC 10-K Filing.pdf")

# Extract elements (skip tables for speed)
print("Extracting text only (no tables) for faster debugging...")
elements = extract_with_pdfplumber(pdf_path, extract_tables=False)

print(f"\n{'='*80}")
print(f"Total elements extracted: {len(elements)}")
print(f"{'='*80}\n")

# Regex patterns (same as in parser.py)
item_pattern = re.compile(r"^Item\s+(\d{1,2}[A-Z]?|X)\b[\.\:]?\s*", re.IGNORECASE)
note_pattern = re.compile(r"^Note\s+(\d+[A-Z]?)\b[\.\:]?\s*", re.IGNORECASE)

# Track which elements contain "Note" but don't match the pattern
note_matches = []
note_near_misses = []

for i, element in enumerate(elements):
    text = str(element).strip()
    el_type = type(element).__name__
    
    # Check for Item or Note matches
    item_match = item_pattern.match(text)
    note_match = note_pattern.match(text)
    
    if item_match:
        print(f"\n[Element {i}] ✓ ITEM MATCH: {el_type}")
        print(f"  Matched: {item_match.group(0)}")
        print(f"  First 200 chars: {text[:200]}")
        
    if note_match:
        print(f"\n[Element {i}] ✓ NOTE MATCH: {el_type}")
        print(f"  Matched: {note_match.group(0)}")
        print(f"  First 200 chars: {text[:200]}")
        note_matches.append((i, text[:200]))
    
    # Check for "Note" keyword that didn't match pattern
    if "note" in text.lower()[:50] and not note_match and el_type == "Text":
        # Get first line
        first_line = text.split('\n')[0][:100]
        if any(word in first_line.lower() for word in ['note 1', 'note 2', 'note 3', 'note 4', 'note 5', 
                                                         'note 6', 'note 7', 'note 8', 'note 9', 'note 10',
                                                         'note 11', 'note 12', 'note 13', 'note 14', 'note 15',
                                                         'note 16', 'note 17', 'note 18', 'note 19', 'note 20']):
            note_near_misses.append((i, el_type, first_line))

print(f"\n{'='*80}")
print(f"SUMMARY:")
print(f"{'='*80}")
print(f"Total Note sections detected by pattern: {len(note_matches)}")
print(f"Potential missed Note headings: {len(note_near_misses)}")

if note_near_misses:
    print(f"\n{'='*80}")
    print(f"POTENTIAL MISSED NOTE HEADINGS:")
    print(f"{'='*80}")
    for i, el_type, first_line in note_near_misses:
        print(f"\n[Element {i}] {el_type}")
        print(f"  First line: {repr(first_line)}")
        print(f"  Why it didn't match: Check for leading whitespace, special chars, or case issues")
