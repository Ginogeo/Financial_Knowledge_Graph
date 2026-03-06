"""
Test script to diagnose retrieval quality
"""

import sys
sys.path.append('src')

from hybrid_search import hybrid_search

# Test query
test_query = "What are the main revenue sources?"

print("=" * 80)
print(f"Query: {test_query}")
print("=" * 80)

primary_text, matched_id, graph_context = hybrid_search(test_query)

print(f"\n📊 Retrieval Stats:")
print(f"  - Primary matched section: {matched_id}")
print(f"  - Number of graph connections: {len(graph_context)}")
print(f"  - Total primary text size: {len(primary_text):,} characters")

print(f"\n📄 Primary Retrieved Content:")
print("-" * 80)

# Show which sections were retrieved
import re
sections = primary_text.split("<hr>")
section_ids = re.findall(r'\*\*Section: ([^*]+)\*\*', primary_text)
print(f"Retrieved {len(section_ids)} unique sections:")
for sid in section_ids:
    print(f"  - {sid}")

print("\n" + "=" * 80)
print("First 2000 characters of primary text:")
print("=" * 80)
# Clean HTML for display
clean_text = re.sub(r'<[^>]+>', '\n', primary_text)
clean_text = re.sub(r'\*\*[^*]+\*\*', '', clean_text)
print(clean_text[:2000])

if graph_context:
    print("\n" + "=" * 80)
    print("Graph Connected Sections:")
    print("=" * 80)
    for ctx in graph_context:
        print(f"\n{ctx['id']}: {len(ctx['text']):,} characters")
        print(f"Preview: {ctx['text'][:200]}...")
