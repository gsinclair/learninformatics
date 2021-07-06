import sys
import os
import yaml
import json
import base64
from pathlib import Path

PRIVATE_DATA_FILENAME = 'etc/datasets/private.yaml'
DATA_TXT_FILENAME = 'DATA.txt'

if Path(os.getcwd()).name != 'learninformatics':
    print('ERROR: run etc/bundle-data.py from project root directory', file=sys.stderr)
    exit()

# This script has one purpose: read the YAML file containing all test data
# and produce nicely formatted Base64 data for inclusion in the public
# Python file.

def load_private_data():
    """Reads the YAML private data and returns a dictionary."""
    raw    = Path(PRIVATE_DATA_FILENAME).read_text()
    cooked = yaml.load(raw)
    return cooked

def base64encode_private_data():
    """Load the private data (dictionary), convert to compact JSON, write it to DATA.txt
       in the root directory."""
    dictionary = load_private_data()
    x = json.dumps(dictionary)
    x = x.encode("ascii")
    x = base64.encodebytes(x)
    x = x.decode("ascii")
    Path(DATA_TXT_FILENAME).write_text(x)


base64encode_private_data()
