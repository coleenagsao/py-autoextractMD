import boto3
import os
from collections import defaultdict
from collections import Counter
from decouple import config     # for .env
import numpy as np
from tkinter import Tk
from tkinter import StringVar
from tkinter.filedialog import askdirectory
from tkinter.ttk import Label
import pandas as pd
import re

def get_map(file_name):
    # add status indicator for processing
    print("[ONGOING]" + form.split("\\")[-1].split(".jpg")[0])

    # save aws_access_key_id and aws_secret_access_key from .env
    key_id = config('aws_access_key_id', default='')
    access_key = config('aws_secret_access_key', default='')

    # define client for textract
    client = boto3.client('textract', region_name='us-east-1',aws_access_key_id=key_id, aws_secret_access_key=access_key)

    # open image and convert to image byte
    with open(file_name, 'rb') as file:
        img_test = file.read()
        bytes_test = bytearray(img_test)

    # process forms and tables using image bytes
    response = client.analyze_document(Document={'Bytes': bytes_test}, FeatureTypes=['FORMS', 'TABLES'])

    # get the text blocks
    blocks = response['Blocks']

    # get key and value maps and table blocks
    key_map = {}
    value_map = {}
    block_map = {}
    table_blocks = []

    for block in blocks:
        block_id = block['Id']
        block_map[block_id] = block
        if block['BlockType'] == "KEY_VALUE_SET":
            if 'KEY' in block['EntityTypes']:
                key_map[block_id] = block
            else:
                value_map[block_id] = block
        if block['BlockType'] == "TABLE":
            table_blocks.append(block)

    return key_map, value_map, block_map, table_blocks

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

def get_rows_columns_map(table_result, blocks_map):
    rows = {}
    for relationship in table_result['Relationships']:
        if relationship['Type'] == 'CHILD':
            for child_id in relationship['Ids']:
                cell = blocks_map[child_id]
                if cell['BlockType'] == 'CELL':
                    row_index = cell['RowIndex']
                    col_index = cell['ColumnIndex']
                    if row_index not in rows:
                        # create new row
                        rows[row_index] = {}
                        
                    # get the text value
                    rows[row_index][col_index] = get_text(cell, blocks_map)
    return rows

def generate_form_csv(keys, values, form, directory):     
    filename = directory + "\\" + form.split("\\")[-1].split(".jpg")[0] + "_form.csv"

    data = np.array([p for p in zip(keys, values)], dtype=object)
    np.savetxt(filename, data, delimiter=',', fmt='%s')
   
def generate_table_csv(table_result, blocks_map, table_index):
    rows = get_rows_columns_map(table_result, blocks_map)

    table_id = 'Table_' + str(table_index)
    
    # get cells
    csv = 'Table: {0}\n\n'.format(table_id)

    for row_index, cols in rows.items():
        for col_index, text in cols.items():
            col_indices = len(cols.items())
            csv += '{}'.format(text) + ","
        csv += '\n'
        
    csv += '\n\n\n'
    return csv
    
# set up window
root = Tk()                                         # create tkinter root window
root.title('AutoExtract MD')
root.geometry("800x600")                            # set window's h and w

subtitle = Label(root, text="Folder: None")
subtitle.pack()

input_dir = askdirectory(title='Select directory for form extraction') 
subtitle.config(text="Folder: " + str(input_dir).split("/")[-1])
root.update()

# put the filenames into a list
forms = []
for filename in os.listdir(input_dir):
    f = os.path.join(input_dir, filename)
    if os.path.isfile(f):
        forms.append(f)    

# create new directory if not existing
directory = "extracted"
if not os.path.exists(directory):
    os.makedirs(directory)

# iterate through the list that calls Amazon Textract APIs 
processed_count = 0
status_text = "(" + str(processed_count) + "/" + str(len(forms)) + ")"
status = Label(root, text=status_text)
status.pack()
data = {}
imported_keys = []
imported_dict = []

for i, form in enumerate(forms):
    text = "(" + str(processed_count) + "/" + str(len(forms)) + ") " + form.split("/")[-1] + " ongoing"
    status.config(text=text)
    root.update()

    filename = form.split("\\")[-1].split(".jpg")[0]
    output_file = directory + "\\" + form.split("\\")[-1].split(".jpg")[0] + "_table.csv"
        
    # generate kv maps and tables
    key_map, value_map, block_map, table_blocks = get_map(form)

    # process forms (key-values)
    kvs = get_kv_relationship(key_map, value_map, block_map)

    # save keys
    imported_keys.append(list(kvs.keys()))
    imported_dict.append(dict(kvs))

        # # process tables (table blocks)
        # csv = ''                                                    # initiate variable to store overall table csv
        # for index, table in enumerate(table_blocks):                # iterate to each table
        #     csv += generate_table_csv(table, block_map, index +1)   # generate csv for each table and add to existing
        #     csv += '\n\n'

        # with open(output_file, "wt") as fout:                       # replace content if existing
        #     fout.write(csv)

    processed_count+=1

    # text segmentation

# get common keys
flattened_list = [word for sublist in imported_keys for word in sublist]
word_set = set(flattened_list)
common_words = set.intersection(*map(set, imported_keys))

# create a dictionary out of the common words
data = {key: [] for key in common_words}

# fill out the dictionary from the forms
for dictionary in imported_dict:
    for key, value in dictionary.items():
        if key in data:
            clean_value = re.sub(r'^\s+|\s+$|,', "", value[0])
            data[key].append(clean_value) # add but clean word

df = pd.DataFrame(data)
print(df)

text = "(" + str(processed_count) + "/" + str(len(forms)) + ") " + "processed"
status.config(text=text)
root.update()

root.mainloop() 

# References:
# https://docs.aws.amazon.com/textract/latest/dg/examples-export-table-csv.html
# https://docs.aws.amazon.com/textract/latest/dg/examples-extract-kvp.html