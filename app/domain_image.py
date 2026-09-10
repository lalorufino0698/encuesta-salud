"""Recover bordered screenshot tables before recognizing individual cells."""
import cv2
import numpy as np
import pymupdf as fitz


def image_tables(raster, tessdata):
    pixels = np.frombuffer(raster.samples, dtype=np.uint8).reshape(raster.height, raster.width, raster.n)
    gray = cv2.cvtColor(pixels[:, :, :3], cv2.COLOR_RGB2GRAY)
    ink = cv2.threshold(gray, 110, 255, cv2.THRESH_BINARY_INV)[1]
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((1, max(30, raster.width // 30)), np.uint8))
    vertical = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((max(20, raster.height // 80), 1), np.uint8))
    grid = cv2.bitwise_or(horizontal, vertical)
    contours, hierarchy = cv2.findContours(grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return []
    groups = {}
    for i, contour in enumerate(contours):
        parent = hierarchy[0][i][3]
        x, y, w, h = cv2.boundingRect(contour)
        if parent < 0 or w < 25 or h < 15 or cv2.contourArea(contour) < w * h * .8:
            continue
        groups.setdefault(parent, []).append((x, y, w, h))
    tables = []
    for boxes in groups.values():
        if len(boxes) < 4:
            continue
        rows = []
        for box in sorted(boxes, key=lambda b: (b[1], b[0])):
            if not rows or abs(rows[-1][0][1] - box[1]) > 8:
                rows.append([])
            rows[-1].append(box)
        values = []
        for row in rows:
            cells = []
            for x, y, w, h in sorted(row):
                crop = pixels[y + 3:y + h - 3, x + 3:x + w - 3, :3].copy()
                if crop.size == 0:
                    cells.append("")
                    continue
                crop = cv2.copyMakeBorder(crop, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=(255, 255, 255))
                pix = fitz.Pixmap(fitz.csRGB, crop.shape[1], crop.shape[0], crop.tobytes(), False)
                with fitz.open("pdf", pix.pdfocr_tobytes(language="spa", tessdata=tessdata)) as cell_pdf:
                    cells.append(cell_pdf[0].get_text(sort=True).strip())
            values.append(cells)
        tables.append(values)
    return tables
