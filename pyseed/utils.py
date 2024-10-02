"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/py-seed/main/LICENSE
"""

import csv
import json
from math import pi, sin
from pathlib import Path

WGS84_RADIUS = 6378137


def _rad(value):
    return value * pi / 180


def _ring_area(coordinates):
    """Calculate the approximate total_area of the polygon were it projected onto
    the earth. Note that this _area will be positive if ring is oriented
    clockwise, otherwise it will be negative.

    Reference:
        Robert. G. Chamberlain and William H. Duquette, "Some Algorithms for
        Polygons on a Sphere", JPL Publication 07-03, Jet Propulsion
        Laboratory, Pasadena, CA, June 2007 http://trs-new.jpl.nasa.gov/dspace/handle/2014/40409

    @Returns

    {float} The approximate signed geodesic total_area of the polygon in square meters.
    """
    if not isinstance(coordinates, (list, tuple)):
        raise ValueError("coordinates must be a list or tuple")

    total_area = 0
    coordinates_length = len(coordinates)

    if coordinates_length > 2:
        for i in range(coordinates_length):
            if i == (coordinates_length - 2):
                lower_index = coordinates_length - 2
                middle_index = coordinates_length - 1
                upper_index = 0
            elif i == (coordinates_length - 1):
                lower_index = coordinates_length - 1
                middle_index = 0
                upper_index = 1
            else:
                lower_index = i
                middle_index = i + 1
                upper_index = i + 2

            p1 = coordinates[lower_index]
            p2 = coordinates[middle_index]
            p3 = coordinates[upper_index]

            total_area += (_rad(p3[0]) - _rad(p1[0])) * sin(_rad(p2[1]))

        total_area = total_area * WGS84_RADIUS * WGS84_RADIUS / 2

    return total_area


def _polygon_area(coordinates):
    if not isinstance(coordinates, (list, tuple)):
        raise ValueError("coordinates must be a list or tuple")

    total_area = 0
    if len(coordinates) > 0:
        total_area += abs(_ring_area(coordinates[0]))

        for i in range(1, len(coordinates)):
            total_area -= abs(_ring_area(coordinates[i]))

    return total_area


def geojson_area(geometry):
    """Calculate the area of a GeoJSON feature. This method is taken from
    a combination of ChatGPT conversion of:
    https://github.com/mapbox/geojson-area/blob/master/index.js
    and
    https://github.com/scisco/area/blob/master/area/__init__.py"""

    if isinstance(geometry, str):
        geometry = json.loads(geometry)

    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a GeoJSON dict")

    total_area = 0

    if geometry["type"] == "Polygon":
        return _polygon_area(geometry["coordinates"])
    elif geometry["type"] == "MultiPolygon":
        for i in range(len(geometry["coordinates"])):
            total_area += _polygon_area(geometry["coordinates"][i])
    elif geometry["type"] == "GeometryCollection":
        for i in range(len(geometry["geometries"])):
            total_area += geojson_area(geometry["geometries"][i])

    return total_area


def read_map_file(mapfile_path):
    """Read in the mapping file"""

    mapfile_path = Path(mapfile_path)
    if not mapfile_path.exists():
        raise ValueError(f"Mapping file {mapfile_path} does not exist")

    with open(mapfile_path) as f:
        map_reader = csv.reader(f)
        map_reader.__next__()  # Skip the header

        # Open the mapping file and fill list
        maplist = []
        for rowitem in map_reader:
            data = {
                "from_field": rowitem[0],
                "from_units": rowitem[1],
                "to_table_name": rowitem[2],
                "to_field": rowitem[3],
            }
            try:
                if rowitem[4].lower().strip() == "true":
                    data["is_omitted"] = True
                else:
                    False
            except IndexError:
                data["is_omitted"] = False

            maplist.append(data)

    return maplist
