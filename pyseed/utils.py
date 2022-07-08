# Imports from Third Party Modules
import csv
from pathlib import Path


def read_map_file(mapfile_path):
    """Read in the mapping file"""

    mapfile_path = Path(mapfile_path)
    assert mapfile_path.exists(), f"Cannot find file: {str(mapfile_path)}"

    map_reader = csv.reader(open(mapfile_path, 'r'))
    map_reader.__next__()  # Skip the header

    # Open the mapping file and fill list
    maplist = list()

    for rowitem in map_reader:
        maplist.append(
            {
                'from_field': rowitem[0],
                'from_units': rowitem[1],
                'to_table_name': rowitem[2],
                'to_field': rowitem[3],
            }
        )

    return maplist
