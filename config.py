from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = str(BASE_DIR / "output")
DEFAULT_PDF_PATH = None
FONT_REGULAR = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"
for name in (FONT_REGULAR, FONT_BOLD):
    pdfmetrics.registerFont(TTFont(name, str(BASE_DIR / "assets" / "fonts" / f"{name}.ttf")))
