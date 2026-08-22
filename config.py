import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Подключаем системные шрифты Windows с поддержкой кириллицы
try:
    pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
    FONT_REGULAR = "Arial"
    FONT_BOLD = "Arial-Bold"
except Exception:
    FONT_REGULAR = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"

OUTPUT_DIR = "output"
DEFAULT_PDF_PATH = os.path.join(OUTPUT_DIR, "act.pdf")
