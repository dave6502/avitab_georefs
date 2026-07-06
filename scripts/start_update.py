#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
import shutil

from download import download
from reorganise import reorganise
from copy_matching_georefs import copy_matching_georefs
from copy_similar_georefs_gui import copy_similar_georefs_gui
from status import status
from src.airac import Airac
from src.utils import airac_to_path, get_team_avitab_zip_paths, download_zip

def print_heading(msg):
    print("\n" '\033[4m' + msg + '\033[0m')

def start_update(airac_cycle):
    airac_new = Airac.from_identifier(airac_cycle)
    airac_prev = airac_new.get_previous()
    airac_new_dir = airac_to_path(airac_new)
    airac_prev_dir = airac_to_path(airac_prev)
    
    try:
        (url, zip_path, extract_dir) = get_team_avitab_zip_paths(airac_prev, airac_new)  
        download_zip(url, zip_path)
        print(f"\nWARNING: Georef zip for {airac_prev}_{airac_new} already exists in TeamAvitab, does {airac_new} really need update?")
        print(f"Continuing anyway ...")
    except:
        pass
        
    print_heading(f"Download previous AIRAC {airac_prev} into {airac_prev_dir} ...")
    print(f"Cmdline equivalent : 'scripts/download.py {airac_prev}'")
    download(str(airac_prev))

    print_heading(f"Reorganise charts in {airac_prev_dir} ...")
    print(f"Cmdline equivalent : 'scripts/reorganise.py {airac_prev_dir.relative_to(Path.cwd())}'")
    reorganise(airac_prev_dir)

    print_heading("Copying hash matching georefs")
    print(f"from TeamAvitab avitab_georefs repo on github")
    print(f"  to {airac_prev_dir}")
    print(f"Cmdline equivalent : 'scripts/copy_matching_georefs.py TeamAvitab {airac_prev_dir.relative_to(Path.cwd())}'")
    got_all_jsons = copy_matching_georefs("TeamAvitab", airac_prev_dir)
    print()
    
    if not got_all_jsons:
        print(f"\nIdeally, all georeference-able aerodrome charts in {airac_prev_dir}")
        print(f"should have had a georef json copied from {prev_georef_dir}")
        print(f"But the copy was incomplete")
        print(f"Please check AIRAC cycle and geoereference dir.")
        print(f"Or, if running an atypical use-case, you'll need to run the scripts individually")
        raise FileNotFoundError(f"Insufficient georef .json files for {airac_prev_dir}")


    print_heading(f"Download new AIRAC {airac_new} into {airac_new_dir} ...")
    print(f"Cmdline equivalent : 'scripts/download.py {airac_new}'")
    download(str(airac_new))

    print_heading(f"Reorganise charts in {airac_new_dir} ...")
    print(f"Cmdline equivalent : 'scripts/reorganise.py {airac_new_dir.relative_to(Path.cwd())}'")
    reorganise(airac_new_dir)

    print_heading("Copying hash matching georefs")
    print(f"from {airac_prev_dir}")
    print(f"  to {airac_new_dir}")
    print(f"Cmdline equivalent : 'scripts/copy_matching_georefs.py {airac_prev_dir.relative_to(Path.cwd())} {airac_new_dir.relative_to(Path.cwd())}'")
    got_all_jsons = copy_matching_georefs(airac_prev_dir, airac_new_dir)
    print()
    
    if got_all_jsons:
        return
        
    print_heading("Starting interactive UI to selectively copy georefs in similar PDFs")
    print(f"Cmdline equivalent : 'scripts/copy_similar_georefs_gui.py {airac_prev_dir.relative_to(Path.cwd())} {airac_new_dir.relative_to(Path.cwd())}'")
    copy_similar_georefs_gui(airac_prev_dir, airac_new_dir)

    print_heading("Status:")
    print(f"Cmdline equivalent : 'scripts/status.py {airac_new_dir.relative_to(Path.cwd())}'")
    status(airac_new_dir)


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]}  4digit_airac_id")
        sys.exit(1)
        
    airac_cycle = sys.argv[1]
    
    try:
        start_update(airac_cycle)
    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        print("\nQuit - WARNING : charts may be left in an inconsistent state")
        
        
if __name__ == "__main__":
    main()
