# This script produces a list of exercise names, numbers and ids
# for processing in the Informatics Leaderboard website

import sys
import os
import yaml
import json
import base64
from pathlib import Path

PRIVATE_DATA_FILENAME = 'etc/datasets/private.yaml'
EXERCISES_FILENAME = 'etc/exercises.txt'

if Path(os.getcwd()).name != 'learninformatics':
    print('ERROR: run etc/print-exercises.py from project root directory', file=sys.stderr)
    exit()

def load_private_data():
    """Reads the YAML private data and returns a dictionary."""
    raw    = Path(PRIVATE_DATA_FILENAME).read_text()
    cooked = yaml.safe_load(raw)
    return cooked

def get_mappings(meta):
    num_to_name = meta['mapping']
    name_to_num = dict()
    for num in num_to_name:
        name = num_to_name[num]
        name_to_num[name] = num
    return name_to_num

def print_exercise_info():
    dictionary = load_private_data()
    mappings = get_mappings(dictionary['meta'])
    for exercise in dictionary:
        if exercise == "xxx" or exercise == "meta":
            continue
        if exercise not in mappings:
            continue
        num = mappings[exercise]
        data = dictionary[exercise]
        line = f"{data['id']} :: {num} :: {data['name']}"
        print(line)

print_exercise_info()

