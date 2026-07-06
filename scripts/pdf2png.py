#!/usr/bin/env python3

import pymupdf
import sys
import re
import os

from PIL import Image


def pdf2png(filename):

    doc = pymupdf.open(filename)
    page = doc[0]
    
    SCALE = 5
    pix = page.get_pixmap(dpi=(72*SCALE))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img.save(re.sub(".pdf", ".png", filename))
             
if __name__ == '__main__':
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        for pdf in sys.argv[1:]:
            print(pdf)
            pdf2png(pdf)
    else:
        print("Usage: %s pdf_filename"%sys.argv[0])
