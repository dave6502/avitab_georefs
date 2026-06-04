#!/usr/bin/env python3

import os
import sys
from pathlib import Path

import re
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils import get_json_hash, get_pdf_hash, is_georefenceable
from src.utils import copy_json, get_pdfs, get_jsons, get_json_path, path_to_airac_id
from src.utils import download_zip, unzip_file
from src.airac import Airac


TEAM_AVITAB_GEOREFS_URL = "https://github.com/dave6502/temp_test_georef/releases/download/RELEASE/TeamAvitabGeorefs.zip"

def get_zip_paths(airac1, airac2):
    url = TEAM_AVITAB_GEOREFS_URL.replace("RELEASE", f"{airac1}_{airac2}")
    zip_name = Path(url).name
    zip_path = Path.cwd() / "charts" / zip_name
    extract_dir = Path.cwd() / "charts" / f"{str(Path(zip_name).stem)}_{airac1}_{airac2}"
    return (url, zip_path, extract_dir)

def download_georefs(new_pdf_dir_path):
    new_airac_id = path_to_airac_id(new_pdf_dir_path)
    new_airac = Airac.from_identifier(new_airac_id)
    prev_airac = new_airac.get_previous()
    next_airac = new_airac.get_next()
    
    try:
        (url, zip_path, extract_dir) = get_zip_paths(prev_airac, new_airac)  
        download_zip(url, zip_path)
    except:
        print(f"Couldn't fetch georefs for {prev_airac}_{new_airac}, try {new_airac}_{next_airac} ...")
        try:
            (url, zip_path, extract_dir) = get_zip_paths(new_airac, next_airac)
            download_zip(url, zip_path)            
        except:
            raise FileNotFoundError(f"Couldn't download TeamAvitab georefs for AIRAC {new_airac}")
    print(f"Downloaded {url}")
        
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    print(f"Unzipping {zip_path}")
    print(f"       to {extract_dir} ...")
    unzip_file(zip_path, extract_dir)
    return extract_dir
    
def copy_matching_georefs(georefs_dir_path, new_pdf_dir_path, verbose = False):
    if not new_pdf_dir_path.exists():
        raise FileNotFoundError(f"{new_pdf_dir_path} (new_pdf_dir) does not exist")
        
    if str(georefs_dir_path) == "TeamAvitab":
        print("Using georefs from TeamAvitab github repo releases")
        georefs_dir_path = download_georefs(new_pdf_dir_path)
    else:
        if not georefs_dir_path.exists():
            raise FileNotFoundError(f"{georefs_dir_path} (georefs_dir) does not exist")
        
    pdfs = get_pdfs(new_pdf_dir_path)
    pdfs = list(filter(lambda x: not get_json_path(x).exists(), pdfs))
    if not pdfs:       
        raise FileNotFoundError(f"{new_pdf_dir_path} (new_pdf_dir_path) has no georeference-able aerodrome pdfs")
        
    jsons = get_jsons(georefs_dir_path)
    if not jsons:       
        raise FileNotFoundError(f"{georefs_dir_path} (georefs_dir) has no georef jsons")

        
    hash_dict = {}
    for json in jsons:
        json_hash = get_json_hash(json)
        hash_dict[json_hash] = json
    no_json_list = []
    count = 0
    for pdf in pdfs:
        pdf_hash = get_pdf_hash(pdf)
        if pdf_hash in hash_dict:
            count += 1
            if not verbose:
                print(f"\rCopying georef .json {count:4} of {len(pdfs)} : {get_json_path(pdf).name[:9]}", end='')
            copy_json(pdf, hash_dict[pdf_hash], verbose)
        else:
            no_json_list.append(pdf)
            
    if not verbose:
        print(f"\rCopied {count} georef .json files" + " " * 20)

    if no_json_list:
        if verbose:
            print(f"Failed to find georef .json files for the following pdfs:")
            last_pdf = Path()
            for pdf in no_json_list:
                if re.findall("/EG[A-Z]{2}_", str(pdf)) != re.findall("/EG[A-Z]{2}_", str(last_pdf)):
                    print()
                print(pdf)
                last_pdf = pdf
        print(f"\n{len(no_json_list)} pdfs of {len(pdfs)} without matching georef .json")
    else:
        print(f"All AIRAC_{path_to_airac_id(new_pdf_dir_path)} aerodrome pdfs georeferenced")
        
    return not no_json_list
    
    
def main():
    if len(sys.argv) != 3:
        print("Usage : " + sys.argv[0] + "  georefs_dir  new_pdf_dir")
        sys.exit(1)
    georefs_dir_path = Path(sys.argv[1])
    new_pdf_dir_path = Path(sys.argv[2])
    
    try:
        copy_matching_georefs(georefs_dir_path, new_pdf_dir_path, verbose = False)
    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        print("\nQuit - WARNING : charts georefs may be left in an incomplete state")

if __name__ == "__main__":
    main()