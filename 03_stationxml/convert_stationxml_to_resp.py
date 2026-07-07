#!/usr/bin/env python

import os
import sys
from flovopy.stationmetadata.convert import convert_stationxml_to_resp

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage:\n  python convert_stationxml_to_resp.py <StationXML> <Output_DIR>")
        sys.exit(1)

    stationxml_path = sys.argv[1]
    output_dir = sys.argv[2]

    convert_stationxml_to_resp(stationxml_path, output_dir)
