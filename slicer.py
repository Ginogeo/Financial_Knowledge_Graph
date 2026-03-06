from pypdf import PdfReader, PdfWriter
import os

# Set up paths dynamically 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
input_pdf = os.path.join(BASE_DIR, "data", "raw", "SEC 10-K Filing.pdf")
output_pdf = os.path.join(BASE_DIR, "data", "raw", "sliced_sample.pdf")

reader = PdfReader(input_pdf)
writer = PdfWriter()

# Let's just grab pages 45 through 55 (where your tables and notes usually are)
for i in range(45, 55):
    writer.add_page(reader.pages[i])

with open(output_pdf, "wb") as f:
    writer.write(f)

print("Created a 10-page sample PDF for fast testing!")