#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
import re
import shutil

from src.utils import get_json_hash, get_pdf_hash, is_georefenceable, get_json_path, get_pdfs, airac_id_to_path
    
def status(charts_dir_path):
    if not charts_dir_path.exists():
        raise FileNotFoundError(f"{charts_dir_path} does not exist")

    pdfs = get_pdfs(charts_dir_path)
    if not pdfs:
        print(f"{charts_dir_path} has no pdfs")
        return
        
    no_json_list = []
    for pdf in pdfs:
        json = get_json_path(pdf)
        if json.exists():
            pdf_hash = get_pdf_hash(pdf)
            json_hash = get_json_hash(json)
            if pdf_hash != json_hash or not json_hash:
                print(f"Hash mismatch for {pdf}")
                print(f"pdf  hash {pdf_hash}")
                print(f"json hash {json_hash}")
        else:
            no_json_list.append(pdf)
            
    if no_json_list:
        print("\nFailed to find georef .json files for the following pdfs:")
        last_pdf = Path()
        for pdf in no_json_list:
            if re.findall("/EG[A-Z]{2}_", str(pdf)) != re.findall("/EG[A-Z]{2}_", str(last_pdf)):
                print()
            print(pdf)
            last_pdf = pdf
        print(f"\n{len(no_json_list)} pdfs without georef .json")
    else:
        print("All aerodrome pdfs georeferenced")
    
def main():
    if len(sys.argv) > 2:
        print("Usage : " + sys.argv[0] + " [charts_dir]")
        sys.exit(1)
        
    if len(sys.argv) == 2:
        charts_dir_paths = [Path(sys.argv[1])]
    else:
        charts_dir_paths = list((Path('.') / "charts").glob("EG_AIRAC_2[0-9][01][0-9]"))
    try:
        for charts_dir_path in charts_dir_paths:
            status(charts_dir_path)
            print("\n")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()
