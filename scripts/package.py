#!/usr/bin/python3

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
import re
import shutil
from pathlib import Path
from datetime import timedelta

from src.utils import get_json_hash, path_to_airac_id
from src.airac import Airac


icao_region_dir = Path("E_NorthernEurope")
icao_country_dir = Path("EG_UnitedKingdom")

def create_additional_files(output_dir, first_airac, last_airac, incremental):
    output_file = Path(output_dir) / "NOT_FOR_REAL_WORLD_NAVIGATION"
    output_file.touch()

    next_airac = last_airac.get_next()
    end_date = next_airac.get_effective() - timedelta(days=1)
    start_date = first_airac.get_effective()
    previous_airac = first_airac.get_previous()
    print(f"Start date AIRAC {first_airac} {start_date.strftime('%a %d %b %Y')}")
    print(f"Last date  AIRAC {last_airac} {end_date.strftime('%a %d %b %Y')}")
    
    with open(Path(output_dir) / "README.txt", 'a') as f:
    
        if incremental:
            base_update_text = f"""
This is an update to be added alongside existing AIRAC content in
MapTiles/Mercator/Calibration in the Avitab Plugins folder.
The Calibration folder must already have the most recent base installed all updates to AIRAC {previous_airac}"""
            from_text = ""
        else:
            base_update_text = f"""
In the Avitab Plugins folder in MapTiles/Mercator/Calibration, remove all previously installed AIRAC cycles for this region
Copy the new "Calibration" folder into MapTiles/Mercator"""
            from_text = "from " + start_date.strftime('%a %d %b %Y')

        f.write(f"""
{output_dir}

NOT TO BE USED FOR REAL WORLD NAVIGATION

Valid {from_text} to {end_date.strftime('%a %d %b %Y')}
{base_update_text}

Some charts are Lambert projection but calibrated as if they are Mercator. There will be some 
inaccuracy in some areas of these charts, but should be OK for flight simulation purposes.

There are some UK AIP charts that contain 2 panels. These may not have calibration or only 1 panel
may be calibrated.
        """)
        

def package(base_ref_dir, airac_path_list):
    hash_set = set()
    
    if base_ref_dir and not base_ref_dir.exists():
        raise FileNotFoundError(f"{base_ref_dir} does not exist")
    for airac_path in airac_path_list:
        if not airac_path.exists():
            raise FileNotFoundError(f"{airac_path} does not exist")
        if not re.match("charts/EG_AIRAC_[0-9]{4}", str(airac_path)):
            raise ValueError(f"{airac_path} is not of format EG_AIRAC_[AIRAC_ID]")
 
    output_dir = Path("georefs") / "TeamAvitab"
    for airac in airac_path_list:
        output_dir = Path(str(output_dir) + "_" + path_to_airac_id(airac))

    if base_ref_dir:
        print(f"Establishing base georeferences from {base_ref_dir} for incremental packaging ...")
        for json_path in base_ref_dir.rglob('*.json'):
            hash_set.add(get_json_hash(json_path))
        output_dir = Path(str(output_dir) + "_Update")
    else:
        output_dir = Path(str(output_dir))
        
    print(f"Copying georef .json files to {output_dir} ...")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    
    for airac_path in airac_path_list:
        airac_path = Path(airac_path)
        for json_path in airac_path.rglob('*.json'):
            json_hash = get_json_hash(json_path)
            if json_hash in hash_set:
                continue
            hash_set.add(json_hash)
            airac = path_to_airac_id(airac_path)
            dst = output_dir / str(airac) / str(icao_region_dir) / str(icao_country_dir) / \
                  re.sub(".*?/EG[A-Z]/", "", str(json_path))
            print(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(json_path, dst)

    first_airac = Airac.from_identifier(path_to_airac_id(airac_path_list[0]))
    last_airac = Airac.from_identifier(path_to_airac_id(airac_path_list[-1]))
    create_additional_files(output_dir, first_airac, last_airac, base_ref_dir)
    
    print("Creating .zip archive ...")
    zip_path = output_dir.parent / "TeamAvitabGeorefs"
    shutil.make_archive(zip_path, 'zip', output_dir)
    print(f"Packaged {output_dir} directory")
    print(f"   into  {str(zip_path) + ".zip"}")



def main():
    parser = argparse.ArgumentParser(
        description="Package the .json files found in the listed AIRAC directories."
    )
    parser.add_argument(
        '-b', '--base',
        help="Optional incremental mode. Only .json files new or changed from the specified base directory will be packaged",
        nargs='?'
    )
    parser.add_argument(
        'input',
        nargs='+',
        help="A list of AIRAC directories of which will be scanned for georef .json files",
    )
    args = parser.parse_args()
  
    airac_path_list = [Path(p) for p in args.input]
    if not airac_path_list:
        parser.print_help()
        sys.exit(1)
        
    base_ref_dir = args.base
    if base_ref_dir:
        base_ref_dir = Path(base_ref_dir)
        
    try:
        package(base_ref_dir, airac_path_list)
    except Exception as e:
        print(e)

        
if __name__ == "__main__":
    main()
