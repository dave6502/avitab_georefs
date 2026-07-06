#!/usr/bin/env python3
""" 
Extract chart names and associated PDF filenames from AIRAC HTML files. 

This module can be used standalone or imported as a module. 
""" 

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse 
import csv 
import re 
import shutil 
from pathlib import Path 
from typing import Dict, List, Optional, Union 
import xml.dom.minidom 

from src.airac import Airac

MAKE_CHANGES = True 
MAX_PATH_LEN = 230 
num_moved_pdfs = 0

try: 
    from bs4 import BeautifulSoup 
except ImportError: 
    print("Error: beautifulsoup4 is required. Install with: pip install beautifulsoup4", file=sys.stderr) 
    sys.exit(1) 

def pretty_print_xml(s: str):
    pretty = xml.dom.minidom.parseString(s.encode()).toprettyxml() 
    pretty = re.sub(r"\n\n*", "\n", pretty) 
    pretty = re.sub(r"\t+\n", "", pretty) 
    print(pretty) 

non_filename_chars = re.compile(r'[^a-zA-Z0-9]') 
def sanitise_description(d):
    """
    Clean up a description string for use in filenames.
    Removes ICAO suffixes, apostrophes and replaces non‑alphanumeric
    characters with underscores, collapsing multiple underscores.
    """
    d = d.replace(" - ICAO","") 
    d = d.replace("'","") 
    d = re.sub(non_filename_chars, '_', d) 
    d = re.sub(r'_+', '_', d) 
    d = d.strip('_') 
    return d 

def shorten_description(d):
    """
    Shorten long chart description identifiers.
    Replaces verbose prefixes with concise abbreviations to keep filenames manageable.
    """
    d = d.replace("STANDARD_ARRIVAL_CHART_INSTRUMENT_STAR_", "STAR_") 
    d = d.replace("STANDARD_INSTRUMENT_DEPARTURE_", "SID_") 
    d = d.replace("STANDARD_DEPARTURE_CHART_INSTRUMENT_SID_", "SID_") 
    d = d.replace("INSTRUMENT_APPROACH_PROCEDURE_", "IAP_") 
    d = d.replace("INSTRUMENT_APPROACH_CHART_", "IAC_") 
    d = d.replace("CONTROL_ZONE_and_CONTROL_AREA_CHART_", "CONTROL_ZONE_") 
    d = d.replace("STANDARD_INSTRUMENT_ARRIVAL_", "STAR_") 
    d = d.replace("APPROACH_TRANSITIONS_CHART_INSTRUMENT_", "APPROACH_TRANSITIONS_") 
    d = re.sub("DELEGATION_of_ATS_RESPONSIBILITIES_WITHIN_", "ATS_RESPONSIBILITIES_", d, flags=re.IGNORECASE) 
    d = re.sub("DELEGATION_of_ATS_RESPONSIBILITIES_", "ATS_RESPONSIBILITIES_", d, flags=re.IGNORECASE) 
    d = d.replace("TEMPORARY_RESERVED_AREAS_GLIDING_in_CLASS_C_AIRSPACE_", "GLIDING_C_AIRSPACE_") 
    d = d.replace("THEORETICAL_NATS_PRIMARY_AND_SECONDARY_RADAR_COVERAGE_", "RADAR_COVERAGE_") 
    d = d.replace("FREQUENCY_ALLOCATIONS_for_MOBILE_INSTALLATION", "MOBILE_FREQ_ALLOC_") 
    d = d.replace("ATS_RESPONSIBILITIES_THE_NORTHWESTERN_CORNER_of_the_SCOTTISH_FIR_UIR_and_ALONG_THE_COMMON_SCOTTISH_and_REYKJAVIK_FIR_UIR_BOUNDARY", 
                  "ATS_RESPONSIBILITIES_SCOTTISH_REYKJAVIK_") 
    d = d.replace("SOUTHERN_NORTH_SEA_ABERDEEN_ATSU_ANGLIA_RADAR_AREA_OF_RESPONSIBILITY_and_ANGLIA_OFFSHORE_SAFETY_AREA_OSA", 
                  "NORTH_SEA_ABERDEEN_ATSU_ANGLIA_RADAR_AREA_OF_RESPONSIBILITY") 
    d = d.replace("HELICOPTER_MAIN_ROUTING_INDICATORS_HMRI_and_NORTHERN_NORTH_SEA_OFF_SHORE_SAFETY_AREA_OSA", 
                  "HELI_ROUTING_INDICATORS_NORTHERN_NORTH_SEA_OFFSHORE_AREA") 
    d = d.replace("NORTHERN_NORTH_SEA_ABERDEEN_ATSU_OFFSHORE_AREAS_of_RESPONSIBILITY_and_QNH_USED", 
                  "NORTH_SEA_ABERDEEN_OFFSHORE_RESPONSIBILITY_QNH") 
    d = d.replace("AIR_GROUND_COMMUNICATION_COVER_EXISTING_in_", "AG_COMM_") 
    d = d.replace("FREE_ROUTE_AIRSPACE_FRA_AND_", "FRA_") 
    d = d.replace("CHART_OF_UNITED_KINGDOM_", "UK_") 
    d = d.replace("CHART_OF_", "") 
    d = d.replace("THE_", "") 
    return d 

def get_section_name(section):
    match section: 
        case 2: return "ADC" 
        case 3: return "OBSTACLE_TERRAIN" 
        case 4: return "SPECIAL_HELI_VISUAL" 
        case 5: return "ATCSMAC" 
        case 6: return "SID" 
        case 7: return "STAR" 
        case 8: return "Approach" 
        case _: 
            print(f"Couldn't match {section}") 
            sys.exit(0) 

def determine_div_id_name(html_file):
    if 'AD-2' in html_file.name:
        return 'AD-2.24'
    elif 'AD-3' in html_file.name:
        return 'AD-3.23'
    else:
        return 'ENR-6'

def extract_metadata(soup, div_id_name):
    """
    Extract chart metadata (description, ICAO code, aerodrome name) from a soup.
    """
    if div_id_name == 'ENR-6':
        description = "Enroute"
        icao, aerodrome_name = 'ENR', ''
        return description, icao, aerodrome_name
    h3 = soup.find('h3')
    if not h3:
        raise ValueError(f"No h3 heading in the aerodrome HTML file")
    raw_text = h3.get_text(strip=True)
    parts = re.split(r'\s*\N{EM DASH}\s*', raw_text)
    if len(parts) != 2:
        raise ValueError("Unable to parse h3 content")
    icao_part = parts[0]
    icao_match = re.search(r'EG[A-Z]{2}', icao_part)
    if icao_match:
        icao = icao_match.group()
    elif 'ENR' in icao_part:
        icao = 'ENR'
    else:
        return None, None
    aerodrome_name = parts[1]
    description = f"{icao}_{sanitise_description(aerodrome_name)}"
    return description, icao, aerodrome_name

def process_chart_entry(name_row, link_row, dir_name, html_file, description, icao, aerodrome_name, verbose):
    """
    Process a single chart entry from a pair of table rows.
 
    Parses the description, determines the ICAO code, builds the new PDF
    filename and path, moves the file if changes are enabled, and returns
    the old and new link information.
    
    Parameters
    ----------
    name_row : Tag
        The table row containing the chart description.
    link_row : Tag
        The following table row containing the link to the PDF.
    dir_name : Path
        Base directory for output PDFs.
    html_file : Path
        Path to the source HTML file.
    description : str
        General description of the chart set.
    icao : str
        ICAO code of the aerodrome (or 'ENR' for en‑route).
    aerodrome_name : str
        Human-readable aerodrome name.
    """
    global num_moved_pdfs
    name_p = name_row.find('p')
    if not name_p:
        return None
    desc_text = name_p.get_text(strip=True)
    if not desc_text:
        return None
    desc_text = sanitise_description(desc_text)
    desc_text = shorten_description(desc_text)
    link_a = link_row.find('a', href=True)
    if not link_a:
        return None
    old_pdf_link = link_a['href']
    chart_ref = link_a.get_text(strip=True)
    aerodrome_icao_pattern = re.compile(r'EG[A-Z]{2}')
    aerodrome_icao = re.findall(aerodrome_icao_pattern, chart_ref)
    if aerodrome_icao:
        icao_used = aerodrome_icao[0]
    elif 'ENR' in chart_ref:
        icao_used = 'ENR'
    else:
        return None
    section_match = re.findall(r'[0-9]+-[0-9]+', chart_ref)
    if not section_match:
        return None
    sec_part = section_match[0]
    sec_num = int(sec_part.split('-')[0])
    index = int(sec_part.split('-')[1])
    new_pdf_basename = f"{icao_used}_{sec_num}_{index:02}_{desc_text}.pdf"
    section_name = get_section_name(sec_num)
    if icao_used == 'ENR':
        new_dir = dir_name / "E" / "EG" / "ENR"
    else:
        new_dir = dir_name / icao_used[0] / icao_used[:2] / icao_used[:3] / \
                  (icao_used + "_" + sanitise_description(aerodrome_name)) / section_name
    new_pdf_path = new_dir / new_pdf_basename
    if len(str(new_pdf_path.resolve())) > MAX_PATH_LEN:
        print(f"Output path too long {len(str(new_pdf_path.resolve()))}:\n{new_pdf_path}")
        sys.exit(0)
    new_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    new_pdf_link = os.path.relpath(new_pdf_path.resolve(), start=html_file.parent.resolve()).replace(os.sep, '/')
    old_pdf_path = (html_file.parent / old_pdf_link).resolve()
    
    if old_pdf_path.exists():
        if MAKE_CHANGES:
            shutil.move(str(old_pdf_path), str(new_pdf_path))
        if verbose:
            print(f"Move {old_pdf_path}")
            print(f"  to {new_pdf_path}")
            print(f"In {html_file.name}, relink {old_pdf_link} -> {new_pdf_link}")
        num_moved_pdfs += 1
    else:
        if "AmdtDeletedAIRAC" not in str(name_row):
            print(f"WARNING : {old_pdf_link} does not exist, linked in {html_file.name} - ignored")
            new_pdf_link = old_pdf_link
        
    return (old_pdf_link, new_pdf_link, str(new_pdf_path))

def process_table(table, dir_name, html_file, description, icao, aerodrome_name, verbose):
    """
    Iterate over a table of chart entries and process each pair of rows.
    
    Calls ``process_chart_entry`` for each chart and aggregates the
    resulting link changes.
    
    Parameters
    ----------
    table : Tag
        BeautifulSoup table element containing chart rows.
    dir_name : Path
        Base directory for output PDFs.
    html_file : Path
        Path to the source HTML file.
    description : str
        General description of the chart set.
    icao : str
        ICAO code of the aerodrome (or 'ENR' for en‑route).
    aerodrome_name : str
        Human-readable aerodrome name.
    
    Returns
    -------
    list
        List of tuples ``(old_pdf_link, new_pdf_link, new_pdf_path)``.
    """
    changes = []
    rows = table.find_all('tr')
    i = 0
    while i < len(rows):
        if i + 1 >= len(rows):
            break
        name_row = rows[i]
        link_row = rows[i + 1]
        result = process_chart_entry(name_row, link_row, dir_name, html_file, description, icao, aerodrome_name, verbose)
        if result:
            changes.append(result)
        i += 2
    return changes

def reorganise_charts_in_html(html_file: Path, dir_name: Path, verbose: bool):
    """
    Reorganise charts for a single HTML file.
    
    Parses the HTML, extracts metadata, processes each chart table,
    updates the HTML with new PDF links, and writes the modified file.
    
    Parameters
    ----------
    html_file : Path
        Path to the HTML file to be processed.
    dir_name : Path
        Base directory where PDFs should be placed.
    """
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    if not re.search("graphics/[0-9]+?.pdf", html_content):
        return
    soup = BeautifulSoup(html_content, 'html.parser')
    div_id_name = determine_div_id_name(html_file)
    section = soup.find('div', id=lambda x: x and div_id_name in x)
    if not section:
        raise ValueError(f"Could not find {div_id_name} section in the HTML file")
    if div_id_name == 'ENR-6':
        description = "Enroute"
        icao, aerodrome_name = 'ENR', ''
    else:
        description, icao, aerodrome_name = extract_metadata(soup, div_id_name)
    tables = section.find_all('table')
    if not tables:
        raise ValueError(f"No tables found in {div_id_name} section")
    for table in tables:
        changes = process_table(table, dir_name, html_file, description, icao, aerodrome_name, verbose)
        for old_link, new_pdf_link, _ in changes:
            if MAKE_CHANGES:
                html_content = html_content.replace(old_link, new_pdf_link)
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

def reorganise(directory: Path, verbose: bool = False):
    global num_moved_pdfs
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    html_files = list(directory.rglob('*.html')) + list(directory.rglob('*.HTML'))
    if not html_files:
        raise FileNotFoundError(f"No HTML files found in {directory}")
    icao_pattern = re.compile(r'EG[A-Z]{2}')
    aerodrome_enr_html_files = [f for f in html_files if icao_pattern.search(f.name) or 'ENR' in f.name]
    if not aerodrome_enr_html_files:
        raise FileNotFoundError(f"No HTML files found with EG[A-Z][A-Z] ICAO code or 'ENR' in filename")
    count = 1
    num_moved_pdfs = 0
    skipped = []
    for html_file in aerodrome_enr_html_files:
        try:
            reorganise_charts_in_html(html_file, directory, verbose)
            if not verbose:
                print(f"\rProcessing {count:3} of {len(aerodrome_enr_html_files)} : {html_file.name}" " "*10, end='')
        except Exception as e:
            skipped.append(html_file.name)
            print(f"Warning: Skipping {html_file}: {e}", file=sys.stderr)
        count += 1
        
    if not verbose:
        print(f"\rReorganised {num_moved_pdfs} pdf charts and relinked {len(aerodrome_enr_html_files)} aerodrome/enroute html files")
        
    if skipped:
        print(f"WARNING : Skipped {len(skipped)} files")
        for s in skipped:
            print(" ", s)

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} airac_dir")
        sys.exit(1)
        
    airac_dir = Path(sys.argv[1])
    
    try:
        reorganise(airac_dir, verbose = False)
    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        print("\nQuit - WARNING : charts may be left in an inconsistent state")

if __name__ == "__main__":
    main()