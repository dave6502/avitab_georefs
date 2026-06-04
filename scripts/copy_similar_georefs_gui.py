#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import re
import pymupdf
import codecs
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk, ImageChops, ImageStat

from src.utils import get_json_hash, get_pdf_hash, is_georefenceable, copy_json, get_pdfs

pdf_pairs = []
pdf_pair_index = 0
image_index = 0

class ComparisonSet:
    """Container for all data related to a PDF comparison."""
    # Global comparison_set will be defined at module level
    def __init__(self, old_pdf, new_pdf):
        self.old_pdf = old_pdf
        self.new_pdf = new_pdf
        self.diff_image, self.old_image, self.new_image = self._create_image_set(old_pdf, new_pdf)
        self.difference_score, self.suggestion = self._suggest_action(self.diff_image, self.old_image, self.new_image)
        self.original_suggested_action = self.suggestion
        self.name = new_pdf.name
        self.images = [self.diff_image, self.old_image, self.new_image]

    def _pdf_to_image(self, filename, scale):
        page = pymupdf.open(filename)[0]
        pix = page.get_pixmap(dpi=int(72 * scale))
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    def _create_image_set(self, old_pdf, new_pdf):
        page = pymupdf.open(old_pdf)[0]
        max_dim = max(abs(page.rect[2] - page.rect[0]),
                      abs(page.rect[3] - page.rect[1]))
        scale = 900 / max_dim
        old_image = self._pdf_to_image(old_pdf, scale)
        new_image = self._pdf_to_image(new_pdf, scale)
        diff_image = ImageChops.difference(old_image, new_image)
        return diff_image, old_image, new_image

    def _suggest_action(self, diff_image, old_image, new_image):
        if old_image.size != new_image.size:
            return "(Resized)", "Reject"
        stat = ImageStat.Stat(diff_image)
        diff_score = int(stat.sum2[0] / stat.count[0])
        if diff_score < 400:
            return diff_score, "Accept"
        elif diff_score > 2000:
            return diff_score, "Reject"
        else:
            return diff_score, "Unknown"


# Global comparison_set variable
comparison_set = None

def _setup_ui(root):
    """Create and layout UI widgets, returning key widget references."""
    style = ttk.Style()
    style.configure('Hint.TLabel', font=('Arial', 12, 'bold'))

    main_frame = ttk.Frame(root, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    image_label = ttk.Label(main_frame)
    image_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))

    info_frame = ttk.Frame(main_frame)
    info_frame.grid(row=1, column=0, columnspan=2, pady=(0, 15), sticky=(tk.W, tk.E))

    suggestion_label = ttk.Label(info_frame, text="", style='Hint.TLabel')
    suggestion_label.grid(row=0, column=0, sticky=tk.W)

    instructions = (
        "Left/Right: Cycle images | "
        "'a': Accept | 'r': Reject | "
        "Enter: Use suggested | "
        "'s': Skip"
    )
    instr_label = ttk.Label(main_frame, text=instructions, font=('Arial', 9))
    instr_label.grid(row=2, column=0, columnspan=2, pady=(0, 10))

    status_label = ttk.Label(main_frame, text="", font=('Arial', 9, 'italic'))
    status_label.configure(width=40)  # fixed width large enough for longest status text
    status_label.grid(row=3, column=0, columnspan=2)

    return image_label, suggestion_label, instr_label, status_label

def run_ui():
    # Initialize the pair index for iteration

    def change_image(inc):
        global image_index
        image_index = (image_index + inc) % 3
        update_display()
        
    def on_key_press(event):
        nonlocal root
        match event.keysym:
            case 'q':
                root.destroy()
            case 'r':
                finalize("Reject")
            case 'a':
                finalize("Accept")
            case 'Return':
                finalize("Suggested")
            case 'Left':
                change_image(-1)
            case 'Right':
                change_image(+1)
            case 's':
                finalize("Skip")
            case _:
                print(f"Key press '{event.keysym}' not handled")
                
    def update_display():
        global image_index
        img = comparison_set.images[image_index]
        photo = ImageTk.PhotoImage(img)
        image_label.configure(image=photo)
        image_label.image = photo
        image_type = ['Diff', 'Old', 'New']
        status_label.configure(text=f"{comparison_set.name} - {image_type[image_index]}")
        colors = {'Accept': 'green', 'Reject': 'red', 'Unknown':'goldenrod'}
        suggestion_label.configure(text=f"Suggest: {comparison_set.suggestion}  " \
                                        f"Score: {comparison_set.difference_score}", \
                                        foreground = colors[comparison_set.suggestion])

    def finalize(classification):
        global pdf_pair_index, image_index, comparison_set
        nonlocal root
              
        if classification == "Suggested" and comparison_set.suggestion == "Unknown":
            return

        if (comparison_set.suggestion == "Accept" and classification == "Reject") or \
           (comparison_set.suggestion == "Reject" and classification == "Accept"):
            comparison_set.suggestion = "Unknown"
            update_display()
            return

        if classification == "Suggested":
            classification = comparison_set.suggestion
            
        print(f"{(pdf_pair_index + 1):3} of {len(pdf_pairs)} " 
              f"{classification:6} (suggested {comparison_set.original_suggested_action:7}, "
              f"diff score {comparison_set.difference_score:9}) {comparison_set.old_pdf.name}")
              
        if classification == "Accept":
            copy_and_patch_json(comparison_set.old_pdf, comparison_set.new_pdf)
                
        if pdf_pair_index >= len(pdf_pairs) - 1:
            root.destroy()
            return
        
        pdf_pair_index += 1
        (old_pdf, new_pdf) = pdf_pairs[pdf_pair_index]
        comparison_set = ComparisonSet(old_pdf, new_pdf)
        image_index = 0
        update_display()
    
    
    root = tk.Tk()
    root.geometry("1000x1000")
    root.resizable(False, False)

    # Initialize UI components
    image_label, suggestion_label, instr_label, status_label = _setup_ui(root)

    root.bind("<KeyPress>", on_key_press)
    root.after(0, update_display)
    
    root.mainloop()

            

def has_sibling_georef(pdf_path):
    json_path = pdf_path.with_suffix(pdf_path.suffix + ".json")
    return json_path.exists()

def has_matching_sibling_georef(pdf_path):
    pdf_hash = get_pdf_hash(pdf_path)
    json_path = pdf_path.with_suffix(pdf_path.suffix + ".json")
    if json_path.exists():
        return pdf_hash == get_json_hash(json_path)
    else:
        return False

def report_pdfs(pdf_files, old_new, dir_path, description):
    if not pdf_files:
        raise FileNotFoundError(f"{dir_path} {old_new}_dir) contains no {description}")
    print(f"Found {len(pdf_files)} {description}")

icao_section_index_regex = re.compile("(EG[A-Z]{2}_[1-8]_[01][0-9]).*.pdf$")
def collect_old_georefed_aerodrome_pdfs(old_pdf_dir_path):
    pdf_files = get_pdfs(old_pdf_dir_path)
    pdf_files = list(filter(lambda p: has_matching_sibling_georef(p), pdf_files))
    report_pdfs(pdf_files, "old", old_pdf_dir_path, "old aerodrome chart (georeference-able) pdfs with matching sibling .json georef")  
    print()    
    return pdf_files
    
def collect_new_non_georefed_aerodrome_pdfs(new_pdf_dir_path):
    pdf_files = get_pdfs(new_pdf_dir_path)
    pdf_files = list(filter(lambda p: not has_sibling_georef(p), pdf_files))
    report_pdfs(pdf_files, "new", new_pdf_dir_path, "new aerodrome chart (georeference-able) pdfs without sibling .json georef")
    print()
    return pdf_files

def collect_pdf_pairs(old_pdf_dir_path, new_pdf_dir_path):
    # Ensure the global list is empty before populating
    global pdf_pairs
    pdf_pairs = []
    """
    Collect a list of pairs of (old, new) pdf path names, in which
       the old pdf has a sibling georef json and
       the new pdf does not have a sibling georef json and
       the old and new pdfs have an identical icao name, section number and index and
       the old and new pdfs have an identical size
    such that the old and new are suitable for comparing. And if they're similar enough
    then the old json can be copied over (with a hash update)
    """
    print(f"Old pdf dir with georefs =    {old_pdf_dir_path}")
    print(f"New pdf dir needing georefs = {new_pdf_dir_path}")
    print()
    old_pdfs = collect_old_georefed_aerodrome_pdfs(old_pdf_dir_path)
    new_pdfs = collect_new_non_georefed_aerodrome_pdfs(new_pdf_dir_path)

    icao_section_index_regex = re.compile("(EG[A-Z]{2}_[1-8]_[0-3][0-9]).*.pdf$")
    for new_pdf in new_pdfs:
        icao_section_index = re.match(icao_section_index_regex, new_pdf.name).group(1)
        for old_pdf in old_pdfs:
            if icao_section_index in old_pdf.name:
                pdf_pairs.append((old_pdf, new_pdf))
    return pdf_pairs

def copy_and_patch_json(old_pdf, new_pdf):
    """
    Copy the JSON from the old PDF to the new PDF (if needed) and patch the hash.
    """
    new_hash = get_pdf_hash(new_pdf)
    old_hash = get_pdf_hash(old_pdf)
    new_json_path = new_pdf.with_suffix(new_pdf.suffix + ".json")
    # Read the original JSON content
    with codecs.open(old_pdf.with_suffix(old_pdf.suffix + ".json"), 'r', encoding='utf-8', errors='ignore') as file:
        json_content = file.read()
    # Patch the hash value
    patched_json = re.sub(old_hash, new_hash, json_content, flags=re.DOTALL)
    # Ensure the target directory exists and write the patched JSON
    Path(new_json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(new_json_path, "w", encoding="utf-8") as file:
        file.write(patched_json)

def copy_similar_georefs_gui(old_pdf_dir_path, new_pdf_dir_path):
    if not old_pdf_dir_path.exists():
        raise FileNotFoundError(f"{old_pdf_dir_path} (old_pdf_dir) does not exist")
    if not new_pdf_dir_path.exists():
        raise FileNotFoundError(f"{new_pdf_dir_path} (new_pdf_dir) does not exist")
        
    pdf_pairs = collect_pdf_pairs(old_pdf_dir_path, new_pdf_dir_path)
    if not pdf_pairs:
        print("No new pdfs found which should be compared with old")
        sys.exit(0)
    
    # Initialize global comparison_set with the first pair
    global comparison_set
    (old_pdf, new_pdf) = pdf_pairs[0]
    comparison_set = ComparisonSet(old_pdf, new_pdf)
    
    run_ui()


def main():
    if len(sys.argv) != 3:
        print("Usage : " + sys.argv[0] + " old_dir new_dir")
        sys.exit(-1)

    old_pdf_dir_path = Path(sys.argv[1])
    new_pdf_dir_path = Path(sys.argv[2])
    
    try:
        copy_similar_georefs_gui(old_pdf_dir_path, new_pdf_dir_path)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()
