#!/usr/bin/env python3
"""wt_engine.py -- a small block-based PDF rendering engine (fpdf2).

It turns a list of content blocks into a paginated, bookmarked PDF with a
table of contents. It is used by generate_walkthrough.py to build the
Smurf/Fraggle lab walkthrough. Keep the engine and the content separate so
the document is easy to maintain.

Block forms (each is a tuple):
    ("h1", text)                  chapter title (starts a new page)
    ("h2", text)                  section title
    ("h3", text)                  sub-section title
    ("p",  text)                  a paragraph
    ("bul", [item, ...])          a bullet list
    ("num", [item, ...])          a numbered list
    ("code", text)                a monospace code / output block
    ("note", title, text)         a highlighted call-out box
    ("table", [rows], [widths])   a table; row 0 is the header
    ("kv", [(key, value), ...])   a key / value definition list
    ("rule",)                     a thin horizontal rule
    ("space", mm)                 vertical space
    ("caption", text)             a small centred caption
"""
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ---- palette (matches the Beamer deck in slides/) ----------------------
PRIMARY = (31, 78, 121)     # router / headings   #1F4E79
AMPC    = (46, 134, 222)    # amplifier subnet    #2E86DE
VICC    = (39, 174, 96)     # victim subnet       #27AE60
ATTC    = (192, 57, 43)     # attacker / danger   #C0392B
AMBER   = (230, 126, 34)    # warnings            #E67E22
INK     = (33, 37, 41)      # body text
MUTE    = (110, 116, 122)   # captions / footer
CODEBG  = (244, 245, 247)   # code background
CODEBD  = (208, 212, 216)   # code border
NOTEBG  = (234, 242, 250)   # note background
RULEC   = (200, 205, 210)

FONTS = {
    ("sans", ""):  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ("sans", "B"): "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ("sans", "I"): "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
    ("mono", ""):  "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ("mono", "B"): "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
}


class Walkthrough(FPDF):
    def __init__(self, title, subtitle, footer_text):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.doc_title = title
        self.doc_subtitle = subtitle
        self.foot = footer_text
        self.set_title(title)
        self.set_author("Group 05, Subsection A2")
        self.set_creator("wt_engine.py (fpdf2)")
        self.set_margins(20, 20, 20)
        self.set_auto_page_break(True, margin=20)
        for (fam, style), path in FONTS.items():
            self.add_font(fam, style, path)
        self.cover = False          # suppress header/footer on cover
        self.plain_pages = set()    # page numbers with no header/footer

    # ---- running header / footer --------------------------------------
    def header(self):
        if self.cover or self.page_no() in self.plain_pages:
            return
        self.set_font("sans", "", 7.5)
        self.set_text_color(*MUTE)
        self.set_y(10)
        self.cell(0, 5, self.doc_subtitle, align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*RULEC)
        self.set_line_width(0.2)
        self.line(20, 16, self.w - 20, 16)
        self.set_y(20)

    def footer(self):
        if self.cover or self.page_no() in self.plain_pages:
            return
        self.set_y(-14)
        self.set_draw_color(*RULEC)
        self.set_line_width(0.2)
        self.line(20, self.h - 15, self.w - 20, self.h - 15)
        self.set_font("sans", "", 7.5)
        self.set_text_color(*MUTE)
        self.cell(0, 6, self.foot, align="L")
        self.set_x(20)
        self.cell(0, 6, f"Page {self.page_no()}", align="R")

    # ---- primitives ---------------------------------------------------
    def _width(self):
        return self.w - self.l_margin - self.r_margin

    def h1(self, text):
        self.add_page()
        self.set_font("sans", "B", 20)
        self.set_text_color(*PRIMARY)
        self.start_section(text, level=0)
        self.multi_cell(0, 9, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*PRIMARY)
        self.set_line_width(0.6)
        y = self.get_y() + 1
        self.line(20, y, self.w - 20, y)
        self.ln(5)
        self.set_text_color(*INK)

    def h2(self, text):
        self._space_guard(24)
        self.ln(2)
        self.set_font("sans", "B", 13.5)
        self.set_text_color(*PRIMARY)
        self.start_section(text, level=1)
        self.multi_cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1.5)
        self.set_text_color(*INK)

    def h3(self, text):
        self._space_guard(20)
        self.ln(1)
        self.set_font("sans", "B", 11)
        self.set_text_color(*AMPC)
        self.start_section(text, level=2)
        self.multi_cell(0, 6, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)
        self.set_text_color(*INK)

    def para(self, text):
        self.set_font("sans", "", 10)
        self.set_text_color(*INK)
        self.multi_cell(0, 5.4, text, align="J",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def caption(self, text):
        self.set_font("sans", "I", 8.5)
        self.set_text_color(*MUTE)
        self.multi_cell(0, 4.6, text, align="C",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)
        self.set_text_color(*INK)

    def bullets(self, items, ordered=False):
        self.set_font("sans", "", 10)
        self.set_text_color(*INK)
        for i, it in enumerate(items, 1):
            marker = f"{i}." if ordered else "•"
            self._space_guard(10)
            x0 = self.get_x()
            self.set_font("sans", "B" if ordered else "", 10)
            self.set_text_color(*PRIMARY if ordered else INK)
            self.cell(8, 5.2, marker, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_font("sans", "", 10)
            self.set_text_color(*INK)
            self.multi_cell(self._width() - 8, 5.2, it, align="L",
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_x(x0)
            self.ln(0.6)
        self.ln(1.6)

    def kv(self, pairs):
        self.set_font("sans", "", 10)
        keyw = 52
        for k, v in pairs:
            self._space_guard(9)
            x0 = self.get_x()
            y0 = self.get_y()
            self.set_font("sans", "B", 10)
            self.set_text_color(*PRIMARY)
            self.multi_cell(keyw, 5.2, k, align="L",
                            new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_xy(x0 + keyw, y0)
            self.set_font("sans", "", 10)
            self.set_text_color(*INK)
            self.multi_cell(self._width() - keyw, 5.2, v, align="L",
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(0.8)
        self.ln(1.4)

    def code(self, text):
        text = text.rstrip("\n")
        self.set_font("mono", "", 7.7)
        line_h = 4.0
        lines = text.split("\n")
        block_h = line_h * len(lines) + 4
        self._space_guard(min(block_h, 60) + 4)
        x0, y0 = self.l_margin, self.get_y()
        w = self._width()
        # background + border drawn per page segment as auto-break may split it
        self.set_fill_color(*CODEBG)
        self.set_draw_color(*CODEBD)
        self.set_line_width(0.2)
        self.set_text_color(30, 30, 30)
        # draw line by line so page breaks are handled by fpdf
        start_y = self.get_y()
        self.set_x(x0)
        # paint a rounded-ish box behind the whole block on this page
        # (simpler: fill each line cell)
        for ln_txt in lines:
            if self.get_y() + line_h > self.h - self.b_margin:
                self.add_page()
            self.set_x(x0)
            self.set_fill_color(*CODEBG)
            self.cell(w, line_h, "  " + ln_txt.replace("\t", "    "),
                      border=0, fill=True,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)
        self.set_text_color(*INK)

    def note(self, title, text, color=None):
        color = color or AMBER
        self.set_font("sans", "", 9.5)
        # measure height
        pad = 3
        self._space_guard(20)
        x0, y0 = self.l_margin, self.get_y()
        w = self._width()
        # render into a temp to know height: use split_only
        self.set_xy(x0 + 5, y0 + pad)
        self.set_font("sans", "B", 9.5)
        self.set_text_color(*color)
        self.multi_cell(w - 8, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(x0 + 5)
        self.set_font("sans", "", 9.5)
        self.set_text_color(*INK)
        self.multi_cell(w - 8, 4.8, text, align="L",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        y1 = self.get_y() + pad
        # draw the box + left accent bar behind (re-draw border now)
        self.set_draw_color(*color)
        self.set_fill_color(*NOTEBG)
        self.set_line_width(0.3)
        self.rect(x0, y0, w, y1 - y0)
        self.set_fill_color(*color)
        self.rect(x0, y0, 1.6, y1 - y0, style="F")
        # re-print text on top of the box
        self.set_xy(x0 + 5, y0 + pad)
        self.set_font("sans", "B", 9.5)
        self.set_text_color(*color)
        self.multi_cell(w - 8, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(x0 + 5)
        self.set_font("sans", "", 9.5)
        self.set_text_color(*INK)
        self.multi_cell(w - 8, 4.8, text, align="L",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(y1)
        self.ln(3)
        self.set_text_color(*INK)

    def table(self, rows, widths=None, align=None, fontsize=8.6):
        if not rows:
            return
        ncol = len(rows[0])
        total = self._width()
        if widths is None:
            widths = [total / ncol] * ncol
        else:
            s = sum(widths)
            widths = [total * x / s for x in widths]
        align = align or ["L"] * ncol
        line_h = 4.7

        def row_height(cells):
            hmax = line_h
            self.set_font("sans", "", fontsize)
            for c, w in zip(cells, widths):
                n = len(self.multi_cell(w - 2, line_h, str(c),
                        dry_run=True, output="LINES"))
                hmax = max(hmax, line_h * max(1, n))
            return hmax + 1.5

        for ridx, cells in enumerate(rows):
            header = (ridx == 0)
            h = row_height(cells)
            if self.get_y() + h > self.h - self.b_margin:
                self.add_page()
                # reprint header on continuation
                if not header:
                    self._table_row(rows[0], widths, align, line_h,
                                    row_height(rows[0]), True, fontsize)
            self._table_row(cells, widths, align, line_h, h, header, fontsize)
        self.ln(3)

    def _table_row(self, cells, widths, align, line_h, h, header, fontsize):
        x0 = self.l_margin
        y0 = self.get_y()
        if header:
            self.set_fill_color(*PRIMARY)
            self.set_text_color(255, 255, 255)
            self.set_font("sans", "B", fontsize)
        else:
            self.set_fill_color(248, 249, 250)
            self.set_text_color(*INK)
            self.set_font("sans", "", fontsize)
        self.set_draw_color(*CODEBD)
        self.set_line_width(0.2)
        x = x0
        for c, w, a in zip(cells, widths, align):
            self.rect(x, y0, w, h, style="DF")
            self.set_xy(x + 1, y0 + 0.8)
            self.multi_cell(w - 2, line_h, str(c), align=a,
                            new_x=XPos.RIGHT, new_y=YPos.TOP)
            x += w
        self.set_xy(x0, y0 + h)

    def rule(self):
        self.ln(1)
        self.set_draw_color(*RULEC)
        self.set_line_width(0.3)
        self.line(20, self.get_y(), self.w - 20, self.get_y())
        self.ln(3)

    def space(self, mm):
        self.ln(mm)

    def _space_guard(self, need):
        if self.get_y() + need > self.h - self.b_margin:
            self.add_page()

    # ---- driver -------------------------------------------------------
    def render(self, blocks):
        dispatch = {
            "h1": lambda a: self.h1(*a),
            "h2": lambda a: self.h2(*a),
            "h3": lambda a: self.h3(*a),
            "p": lambda a: self.para(*a),
            "bul": lambda a: self.bullets(a[0], ordered=False),
            "num": lambda a: self.bullets(a[0], ordered=True),
            "code": lambda a: self.code(*a),
            "note": lambda a: self.note(*a),
            "table": lambda a: self.table(*a),
            "kv": lambda a: self.kv(*a),
            "rule": lambda a: self.rule(),
            "space": lambda a: self.space(*a),
            "caption": lambda a: self.caption(*a),
        }
        for block in blocks:
            kind, args = block[0], block[1:]
            dispatch[kind](args)
