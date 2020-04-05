#!/usr/bin/env python3

import csv
import io
import json
import os
import re
import zipfile

from enum import Enum

BASEDIR = os.path.dirname(os.path.realpath(__file__))

NAMES_ZIP = os.path.join(BASEDIR, "names.zip")
TOTALS_HTML = os.path.join(BASEDIR, "numberUSbirths.html")
OUTPUT_JSON = os.path.join(BASEDIR, "national-data.json")

FILENAME_RE = re.compile("yob([0-9]{4})\.txt")

NAMES = { "F": {}, "M": {} }
MIN_YEAR = None
MAX_YEAR = None

# Read the data by name and year out of NAMES_ZIP.
zf = zipfile.ZipFile(NAMES_ZIP, "r")
for f in zf.namelist():
    if f == "NationalReadMe.pdf":
        continue
    m = FILENAME_RE.fullmatch(f)
    if m is None:
        raise AssertionError("Unexpected filename {}.".format(f))
    year = int(m[1])

    if MIN_YEAR is None:
        MIN_YEAR = year
        MAX_YEAR = year
    else:
        if year < MIN_YEAR:
            MIN_YEAR = year
        if year > MAX_YEAR:
            MAX_YEAR = year

    f_io = zf.open(f, mode="r")
    data = csv.reader(io.TextIOWrapper(f_io))
    for (name, sex, number) in data:
        NAMES[sex].setdefault(name, {})[year] = int(number)
    f_io.close()
zf.close()

YEAR_RANGE = range(MIN_YEAR, MAX_YEAR + 1)

# Convert the hashes-by-year to arrays offset by MIN_YEAR (i.e., where
# array[n] is the data for the year MIN_YEAR+n).
for sex in NAMES:
    sex_dict = NAMES[sex]
    for name in sex_dict:
        oldval = sex_dict[name]
        sex_dict[name] = [oldval.get(year, 0) for year in YEAR_RANGE]

# Read the totals out of TOTALS_HTML.
YEAR_RE = re.compile("<tr><td>([0-9]{4})</td>")
NUMBERS_RE = re.compile("<td>([0-9,]+)</td><td>([0-9,]+)</td><td>([0-9,]+)</td></tr>")
class TableState(Enum):
    HEADER = 1
    YEAR_LINE = 2
    NUMBERS_LINE = 3
    FOOTER = 4
total_state = TableState.HEADER
total_io = open(TOTALS_HTML, "r")
year = None
previous_year = MIN_YEAR - 1
male_totals = []
female_totals = []
for line in total_io:
    line = line.rstrip("\r\n")
    if total_state == TableState.HEADER:
        if line == "<tbody>":
            total_state = TableState.YEAR_LINE
    elif total_state == TableState.YEAR_LINE:
        if line == "          </tbody>":
            total_state = TableState.FOOTER
            break # don't bother processing the lines in FOOTER state
        m = YEAR_RE.fullmatch(line)
        if m is None:
            raise AssertionError("Unexpected line {}.".format(line))
        year = int(m[1])
        if previous_year + 1 != year:
            raise AssertionError("Unexpected year {}.".format(year))
        previous_year = year
        total_state = TableState.NUMBERS_LINE
    elif total_state == TableState.NUMBERS_LINE:
        m = NUMBERS_RE.fullmatch(line)
        if m is None:
            raise AssertionError("Unexpected line {}.".format(line))
        male_total = int(m[1].replace(",",""))
        female_total = int(m[2].replace(",",""))
        male_totals += [male_total]
        female_totals += [female_total]
        if int(m[3].replace(",","")) != male_total + female_total:
            raise AssertionError("Incorrect totals for year {}.".format(year))
        total_state = TableState.YEAR_LINE
total_io.close()
if previous_year != MAX_YEAR:
    raise AssertionError("Maximum year mismatch ({} from zip, {} from HTML).".format(MAX_YEAR, previous_year))

output_io = open(OUTPUT_JSON, "w")
json.dump({ "male_totals": male_totals,
            "female_totals": female_totals,
            "male_names": NAMES["M"],
            "female_names": NAMES["F"],
            "min_year": MIN_YEAR,
            "max_year": MAX_YEAR },
          output_io,
          sort_keys = True)
output_io.close()
