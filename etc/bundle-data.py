import sys
import os.path
import json
import base64
import hashlib
from pathlib import Path
from io import StringIO
from random import randint

PRIVATE_DATA_FILENAME = 'etc/datasets/private.json'
DATA_TXT_FILENAME = 'DATA.txt'

if Path(os.getcwd()).name != 'learninformatics':
    print('ERROR: run etc/bundle-data.py from project root directory', file=os.stderr)
    exit()

# This script has one purpose: read the JSON file containing all test data
# and produce nicely formatted Base64 data for inclusion in the public
# Python file.

def load_private_data():
    """Returns hash of informatics data."""
    return json.loads(Path(PRIVATE_DATA_FILENAME).read_text())

def base64encode_private_data():
    """Load the private data, compress it by converting back to non-pretty
       JSON, base64-encode it, and write it to DATA.txt in the root directory."""
    x = load_private_data()
    x = json.dumps(x)
    x = x.encode("ascii")
    x = base64.encodebytes(x)
    x = x.decode("ascii")
    Path(DATA_TXT_FILENAME).write_text(x)

base64encode_private_data()
