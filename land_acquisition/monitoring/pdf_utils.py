"""Lightweight pure-Python PDF 1.4 report generator with pagination and table formatting."""


def _escape_pdf_text(text):
    """Escape special characters for PDF literal strings and normalize non-ASCII."""
    safe = str(text).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    return safe.encode('ascii', 'replace').decode('ascii')


def generate_table_pdf(title, headers, rows, subtitle=''):
    """Generate a multi-page A4 landscape PDF document containing a formatted table."""
    page_width = 842
    page_height = 595
    margin_x = 36
    top_y = page_height - 45
    line_height = 15
    rows_per_page = 30

    col_count = max(len(headers), 1)
    usable_width = page_width - 2 * margin_x
    col_width = usable_width / col_count
    max_chars = max(int(col_width / 5.2), 8)

    def format_row(cells):
        parts = []
        for idx, cell in enumerate(cells):
            text = str(cell or '')
            if len(text) > max_chars:
                text = text[: max_chars - 2] + '..'
            parts.append((margin_x + idx * col_width, text))
        return parts

    pages_content = []
    total_rows = rows if rows else [['No records found.'] + [''] * (col_count - 1)]

    for page_idx in range(0, len(total_rows), rows_per_page):
        chunk = total_rows[page_idx : page_idx + rows_per_page]
        cmds = ['BT']
        # Title
        cmds.append('/F2 14 Tf')
        cmds.append(f'1 0 0 1 {margin_x} {top_y} Tm ({_escape_pdf_text(title)}) Tj')
        if subtitle:
            cmds.append('/F1 9 Tf')
            cmds.append(f'1 0 0 1 {margin_x} {top_y - 16} Tm ({_escape_pdf_text(subtitle)}) Tj')

        y = top_y - 38
        # Header row
        cmds.append('/F2 8 Tf')
        for x_pos, text in format_row(headers):
            cmds.append(f'1 0 0 1 {x_pos:.1f} {y} Tm ({_escape_pdf_text(text)}) Tj')

        y -= 6
        cmds.append('ET')
        cmds.append(f'0.4 w {margin_x} {y} m {page_width - margin_x} {y} l S')
        y -= 14

        cmds.append('BT')
        cmds.append('/F1 8 Tf')
        for row in chunk:
            for x_pos, text in format_row(row):
                cmds.append(f'1 0 0 1 {x_pos:.1f} {y} Tm ({_escape_pdf_text(text)}) Tj')
            y -= line_height

        # Footer
        page_num = (page_idx // rows_per_page) + 1
        cmds.append('/F1 8 Tf')
        cmds.append(f'1 0 0 1 {margin_x} 24 Tm (National Land Acquisition & Management System - Page {page_num}) Tj')
        cmds.append('ET')
        pages_content.append('\n'.join(cmds))

    # Build PDF objects
    objects = []
    # 1: Catalog, 2: Pages, 3: Font Regular, 4: Font Bold
    objects.append('<< /Type /Catalog /Pages 2 0 R >>')
    page_obj_ids = []
    next_id = 5
    page_objects = []
    for content in pages_content:
        content_bytes = content.encode('latin-1', 'replace')
        content_id = next_id
        page_id = next_id + 1
        next_id += 2
        page_obj_ids.append(f'{page_id} 0 R')
        page_objects.append((
            content_id,
            f'<< /Length {len(content_bytes)} >>\nstream\n{content}\nendstream',
            page_id,
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] '
            f'/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>',
        ))

    objects.append(f'<< /Type /Pages /Kids [{" ".join(page_obj_ids)}] /Count {len(page_obj_ids)} >>')
    objects.append('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    objects.append('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>')
    for _, stream_obj, _, page_obj in page_objects:
        objects.append(stream_obj)
        objects.append(page_obj)

    pdf_parts = ['%PDF-1.4\n']
    offsets = []
    for idx, obj in enumerate(objects, start=1):
        offsets.append(sum(len(p.encode('latin-1', 'replace')) for p in pdf_parts))
        pdf_parts.append(f'{idx} 0 obj\n{obj}\nendobj\n')

    xref_offset = sum(len(p.encode('latin-1', 'replace')) for p in pdf_parts)
    pdf_parts.append(f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n')
    for off in offsets:
        pdf_parts.append(f'{off:010d} 00000 n \n')
    pdf_parts.append(f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF')

    return ''.join(pdf_parts).encode('latin-1', 'replace')
