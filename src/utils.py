#!/usr/bin/env python3
"""
Shared utility functions for AIRAC chart operations.

This module provides common functions used across multiple scripts for:
- Calculating SHA256 hashes of PDF files
- Extracting hash values from JSON files
- Filtering charts based on georeferencing rules
- Working with AIRAC cycles and directories
"""

import hashlib
import re
import shutil
import requests
import zipfile
from pathlib import Path

from src.airac import Airac


def get_json_hash(f: Path) -> str:
    """Given a JSON georeferencing file, return the SHA256 hash it contains"""
    with open(f, 'r') as file:
        text = file.read()
        hash_text = re.findall("\"hash\": \"([0-9a-f]+)\"", text)
        if len(hash_text) == 1:
            return hash_text[0]
    return ""


def get_pdf_hash(f: Path) -> str:
    """Given a PDF file, return its SHA256 hash"""
    with open(f, 'rb') as file:
        bytes_data = file.read()
        hash_text = hashlib.sha256(bytes_data).hexdigest()
    return hash_text


def get_json_path(pdf_path: Path) -> Path:
    """Get the pathname of the sibling .json file of a PDF"""
    json_path = pdf_path.with_suffix(pdf_path.suffix + ".json")
    return json_path


def is_georefenceable(pdf: Path) -> bool:
    """
    Check if a PDF chart is suitable for georeferencing.
    Excludes charts that contain coding tables, visual profiles, and other
    special content that should not be georeferenced.
    Returns True if the PDF can be georeferenced, False otherwise
    """
    pdf_str = str(pdf)
    if "_CODING_TABLES_" in pdf_str or \
       "_CODING_TABLE_" in pdf_str or \
       "_DE_ICING_PADS" in pdf_str or \
       "_TEXT" in pdf_str or \
       "_VISUAL_APPROACH_PROFILE_" in pdf_str or \
       "STAND_COORDINATES" in pdf_str or \
       "_CODING_DATA_" in pdf_str:
        return False
    return True


def airac_to_path(airac: Airac) -> Path:
    """Given an AIRAC object, return the path of the charts for that AIRAC cycle"""
    return Path.cwd() / "charts" / f"EG_AIRAC_{airac.get_year() % 100:02d}{airac.get_ordinal():02d}"


def airac_id_to_path(airac_id: str) -> Path:
    """Given a 4 digit AIRAC cycle identifier, return the path of the charts for that AIRAC cycle"""
    airac = Airac.from_identifier(airac_id)
    return airac_to_path(airac)


def path_to_airac_id(airac_path: Path) -> str:
    """Given a path to AIRAC charts, return the 4 digit AIRAC cycle identifier"""
    path_str = str(airac_path)
    # Extract the last 4 digits from the path (YYOO format)
    match = re.search(r'EG_AIRAC_([0-9]{4})', path_str)
    if match:
        return match.group(1)
    # Fallback to last 4 characters if pattern doesn't match
    return path_str[-4:]


def get_pdfs(dir_path: Path):
    """
    Scan a directory for all georeference-able aerodrome PDF files.
    Returns a list of Path objects.
    """
    print(f"Finding aerodrome chart pdfs in {dir_path} ...")
    pdf_files = list(dir_path.rglob('*.pdf'))
    icao_regex = re.compile("[^A-Z]EG[A-Z]{2}[^A-Z]")
    pdf_files = list(filter(lambda x: re.search(icao_regex, str(x)), pdf_files))
    pdf_files = list(filter(lambda x: is_georefenceable(x), pdf_files))
    if not pdf_files:
        print(f"WARNING : {dir_path} contains no aerodrome chart pdfs")
    return pdf_files


def get_jsons(dir_path: Path):
    """
    Scan a directory for georef JSON files matching the ICAO pattern.
    Returns a list of Path objects.
    """
    print(f"Finding georef .json files in {dir_path} ...")
    icao_regex = re.compile("[^A-Z]EG[A-Z]{2}[^A-Z]")
    json_files = list(dir_path.rglob('*.json'))
    json_files = [j for j in json_files if icao_regex.search(str(j))]
    if not json_files:
        print(f"WARNING : {dir_path} contains no georef .json files")
    return json_files


def copy_json(pdf: Path, json_file: Path, verbose: bool = True) -> None:
    """Copy a JSON file next to its PDF if the target does not already exist."""
    new_json = pdf.with_suffix(pdf.suffix + ".json")
    if not new_json.exists():
        shutil.copy(json_file, new_json)
    if verbose:
        print(f"Copy {json_file}")
        print(f"  to {new_json}")


def ensure_dir(path: Path) -> None:
    """Ensure that a directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    
def download_zip(url: str, output_path: Path) -> None:
    """Download a file with a simple retry using a Session (allows mocking)."""
    for attempt in range(3):
        try:
            session = requests.Session()
            response = session.get(url, stream=True, timeout=10)
            response.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return
        except Exception as e:
            pass
    raise RuntimeError(f"Failed to download {url}")

def unzip_file(zip_path: Path, extract_to: Path) -> None:
    """Extract zip contents."""
    extract_to.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)


def get_team_avitab_zip_paths(airac1, airac2):
    TEAM_AVITAB_GEOREFS_URL = "https://github.com/dave6502/temp_test_georef/releases/download/RELEASE/TeamAvitabGeorefs.zip"
    url = TEAM_AVITAB_GEOREFS_URL.replace("RELEASE", f"{airac1}_{airac2}")
    zip_name = Path(url).name
    georefs_dir = Path.cwd() / "georefs"
    ensure_dir(georefs_dir)
    zip_path = georefs_dir / zip_name
    extract_dir = georefs_dir / f"{str(Path(zip_name).stem)}_{airac1}_{airac2}"
    return (url, zip_path, extract_dir)
