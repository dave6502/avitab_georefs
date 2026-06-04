#!/usr/bin/env python3

import os
import sys
from pathlib import Path

import shutil
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.airac import Airac
from src.utils import airac_id_to_path, download_zip, unzip_file


BASE_URL = "https://nats-uk.ead-it.com/cms-nats/export/sites/default/en/Publications/AIP/HTML_AIP/"

def get_nats_aip_html_zip_url(airac: Airac) -> str:
    """Return the NATS Offline HTML Download zip URL for the given cycle."""
    year, cycle = airac.get_year() % 100, airac.get_ordinal()
    return f"{BASE_URL}AIRAC-{cycle:02d}-{year:02d}.zip"

def check_airac_downloadable(airac: Airac):
    current_airac = Airac.from_instant(datetime.now(timezone.utc))
    next_airac = current_airac.get_next()
    next_plus1_airac = next_airac.get_next()
    if airac not in [current_airac, next_airac, next_plus1_airac]:
        raise RuntimeError("Invalid AIRAC cycle to download - UK AIP only hosts zips for the current, next and next+1 cycles")
        
def clean_dir(airac_dir):
    for d in airac_dir.glob("*"):
        if d.suffix != ".zip":
            print(f"Delete {d}")
            shutil.rmtree(d)

def download(cycle_identifier: str) -> Path:
    """Download and extract the AIRAC zip."""
    # Validate cycle identifier
    if not cycle_identifier.isdigit() or len(cycle_identifier) != 4:
        raise ValueError("Invalid AIRAC cycle identifier. Must be a 4-digit number.")
    
    airac = Airac.from_identifier(cycle_identifier)
    
    url = get_nats_aip_html_zip_url(airac)
    zip_name = Path(url).name
    
    output_dir = airac_id_to_path(cycle_identifier)
    clean_dir(output_dir)
    zip_path = output_dir / zip_name
    extract_dir = output_dir / Path(zip_name).stem
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not zip_path.exists():
        check_airac_downloadable(airac)
        print(f"Downloading {url} ...")
        download_zip(url, zip_path)
        print(f"Downloaded {url}")
    else:
        print(f"Using cached zip {zip_path}")

    print(f"Unzipping {zip_path}")
    print(f"       to {extract_dir} ...")
    unzip_file(zip_path, extract_dir)
    return output_dir

def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} 4digit_airac_id")
        sys.exit(1)
        
    airac_cycle = sys.argv[1]
    
    try:
        download(airac_cycle)
    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        print("\nQuit - WARNING : charts may be left in an inconsistent state")

if __name__ == "__main__":
    main()