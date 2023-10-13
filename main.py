import boto3
import os
import re
from collections import defaultdict
from decouple import config     # for .env
import numpy as np

def get_kv_map(file_name):
    # save aws_access_key_id and aws_secret_access_key from .env
    key_id = config('aws_access_key_id', default='')
    access_key = config('aws_secret_access_key', default='')

    with open(file_name, 'rb') as file:
        img_test = file.read()
        bytes_test = bytearray(img_test)
        print('Image loaded', file_name)

    # define client for textract
    client = boto3.client('textract', region_name='us-east-1',aws_access_key_id=key_id, aws_secret_access_key=access_key)
    
    # add status indicator for processing
    print("[ONGOING]" + form);

    # process using image bytes
    response = client.analyze_document(Document={'Bytes': bytes_test}, FeatureTypes=['FORMS'])

    # Get the text blocks
    blocks = response['Blocks']

    # get key and value maps
    key_map = {}
    value_map = {}
    block_map = {}
    for block in blocks:
        block_id = block['Id']
        block_map[block_id] = block
        if block['BlockType'] == "KEY_VALUE_SET":
            if 'KEY' in block['EntityTypes']:
                key_map[block_id] = block
            else:
                value_map[block_id] = block

    return key_map, value_map, block_map

def get_kv_relationship(key_map, value_map, block_map):
    kvs = defaultdict(list)
    for block_id, key_block in key_map.items():
        value_block = find_value_block(key_block, value_map)
        key = get_text(key_block, block_map)
        val = get_text(value_block, block_map)
        kvs[key].append(val)
    return kvs

def find_value_block(key_block, value_map):
    for relationship in key_block['Relationships']:
        if relationship['Type'] == 'VALUE':
            for value_id in relationship['Ids']:
                value_block = value_map[value_id]
    return value_block

def get_text(result, blocks_map):
    text = ''
    if 'Relationships' in result:
        for relationship in result['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    word = blocks_map[child_id]
                    if word['BlockType'] == 'WORD':
                        text += word['Text'] + ' '
                    if word['BlockType'] == 'SELECTION_ELEMENT':
                        if word['SelectionStatus'] == 'SELECTED':
                            text += 'X '

    return text

def print_kvs(kvs):
    for key, value in kvs.items():
        print(key, ":", value)

def generate_csv(kvs, form, directory): 
    keys = list(kvs.keys())
    values = list(kvs.values())
    filename = directory + "\\" + form.split("\\")[-1].split(".jpg")[0] + ".csv"

    data = np.array([p for p in zip(keys, values)], dtype=object)
    np.savetxt(filename, data, delimiter=',', fmt='%s')

def search_value(kvs, search_key):
    for key, value in kvs.items():
        if re.search(search_key, key, re.IGNORECASE):
            return value

# save filenames
directory = 'images'
forms = []

for filename in os.listdir(directory):
    f = os.path.join(directory, filename)
    if os.path.isfile(f):
        forms.append(f)    # put the filenames into a list

# create new directory if not existing
directory = "extracted"
if not os.path.exists(directory):
    os.makedirs(directory)

for i, form in enumerate(forms):
    key_map, value_map, block_map = get_kv_map(form)

    # get key-value relationship
    kvs = get_kv_relationship(key_map, value_map, block_map)

    generate_csv(kvs, form, directory)

    print("[DONE] " + form)