"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/py-seed/main/LICENSE
"""

import unittest
from pathlib import Path

from pyseed.utils import read_map_file


class UtilsTest(unittest.TestCase):
    def test_mapping_file(self):
        mappings = read_map_file(Path("tests/data/test-seed-data-mappings.csv"))
        assert len(mappings) == 14

        expected = {
            "from_field": "Sq. Ft",
            "from_units": "ft**2",
            "to_field": "gross_floor_area",
            "to_table_name": "PropertyState",
            "is_omitted": False,
        }
        assert mappings[5] == expected
