import boto3                                # for Amazon Textract API
from decouple import config                 # for reading credentials in .env
import os                                   # for reading directories 

# modules for dataframe, data, and cleaning
import re
from collections import defaultdict
import pandas as pd
import matplotlib.pyplot as plt

# modules for GUI
from tkinter import Tk, ttk
from tkinter.ttk import Label, LabelFrame, Scrollbar
from tkinter import *
from tkinter.filedialog import askdirectory

# modules for encryption
from cryptography.fernet import Fernet 

# function that given a folder, it iterates to all the files inside and returns the keys, values, blocks
def get_map(folder):
    key_map = {}
    value_map = {}
    block_map = {}
    table_blocks = []

    # iterate inside the folder
    for file in os.listdir(folder):    
        filename = os.path.join(folder, file)
        print("[ONGOING] " + filename)              # display status indicator in terminal

        # access aws_access_key_id and aws_secret_access_key from .env and save to variables
        key_id = config('aws_access_key_id', default='')
        access_key = config('aws_secret_access_key', default='')

        # define client for textract
        client = boto3.client('textract', region_name='us-east-1',aws_access_key_id=key_id, aws_secret_access_key=access_key)

        # open image and convert to image byte
        with open(filename, 'rb') as file:
            img_test = file.read()
            bytes_test = bytearray(img_test)

        # process forms and tables using image bytes
        response = client.analyze_document(Document={'Bytes': bytes_test}, FeatureTypes=['FORMS', 'TABLES'])

        # get the text blocks
        blocks = response['Blocks']

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

# function that returns the text in the block
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

# function that returns the value
def find_value_block(key_block, value_map):
    for relationship in key_block['Relationships']:
        if relationship['Type'] == 'VALUE':
            for value_id in relationship['Ids']:
                value_block = value_map[value_id]
    return value_block

# function that creates a defaultdict out of the keys, values got
def get_kv_relationship(key_map, value_map, block_map):
    kvs = defaultdict(list)
    for block_id, key_block in key_map.items():
        value_block = find_value_block(key_block, value_map)
        key = get_text(key_block, block_map)
        val = get_text(value_block, block_map)
        kvs[key].append(val)
    return kvs

# function that cleans the content of the frame in GUI
def clear_data():
    tv1.delete(*tv1.get_children())
    return None

# function that encrypts a csv using Fernet and returns a encrypted csv
def encrypt_data(filename):
    key = Fernet.generate_key()

    with open(filename, 'rb') as file:
        data = file.read()
    
    cipher_suite = Fernet(key)
    encrypted_data = cipher_suite.encrypt(data)

    with open(filename, 'wb') as file:
        file.write(encrypted_data)

# function that pops out a pie chart given a variable chosen by user after generation of dataframe
def display_visualization():
    plt.clf()
    counts = df[variable.get()].value_counts()
    counts.plot.pie(autopct='%1.1f%%')
    plt.axis('equal')
    plt.show()

# set up window
root = Tk()                                         # create tkinter root window
root.title('AutoExtractMD')                         # set title         
root.geometry("700x600")                            # set dimensions               
root.wm_iconbitmap('logo.ico')                      # change default icon to a D icon
root.pack_propagate(False)                          # set window's h and w

# create label frame for container of the dataframe's content
frame1 = LabelFrame(root, text="Data")
frame1.place(height=270, width=700)

# create label frame for indicators of files being processed
file_frame = LabelFrame(root, text="Status Indicator")
file_frame.place(height=100, width=700, rely=0.5, relx=0)

# create label frame for buttons for visualization
analysis_frame = LabelFrame(root, text="Visualization Options")
analysis_frame.place(height=150, width=700, rely=0.70, relx=0)

# create a treeview Widget
tv1 = ttk.Treeview(frame1)
tv1.place(relheight=1, relwidth=1)                                      # set the hw of the widget to 100% of its container
treescrolly = Scrollbar(frame1, orient="vertical", command=tv1.yview)   # update the yaxis view of the widget
treescrollx = Scrollbar(frame1, orient="horizontal", command=tv1.xview) # update the xaxis view of the widget
tv1.configure(xscrollcommand=treescrollx.set, yscrollcommand=treescrolly.set) # assign the scrollbars to the Treeview Widget
treescrollx.pack(side="bottom", fill="x")           # make the scrollbar fill the x axis of the Treeview widget
treescrolly.pack(side="right", fill="y")            # make the scrollbar fill the y axis of the Treeview widget

# display one of the status indicators (folders chosen)
subtitle = Label(root, text="Folder: None")         # set the initial folder chosen to be None
subtitle.place(rely=0.55, relx=0.05)

# display a dialog box that asks user to chose a folder
input_dir = askdirectory(title='Select directory for form extraction') 
subtitle.config(text="Folder: " + str(input_dir).split("/")[-1])    # after choosing, update the chosen folder
root.update()

# save the names of the folders inside the chosen folder
folders = []
for main, dirs, files in os.walk(input_dir):
    for dir in dirs:
        dir_path = os.path.join(main, dir)      # get the full path of the directory
        folders.append(dir_path)

processed_count = 0         # set count of processed files to 0
imported_keys = []          # initialize array for keys of every inner folder
imported_dict = []          # initialize array for dictionary of every inner folder

# display another status indicator of how many files is being processed like (0/2)
status_text = "(" + str(processed_count) + "/" + str(len(folders)) + ")"
status = Label(root, text=status_text)
status.place(rely=0.6, relx=0.05)

# iterate in each inner folder
for i, folder in enumerate(folders):
    # update status indicator in GUI if processed count is updated
    text = "(" + str(processed_count) + "/" + str(len(folders)) + ") " + folder.split("/")[-1] + " ongoing"
    status.config(text=text)
    root.update()

    # generate kv maps and tables
    key_map, value_map, block_map, table_blocks = get_map(folder)

    # process forms (key-values)
    kvs = get_kv_relationship(key_map, value_map, block_map)

    # save keys
    imported_keys.append(list(kvs.keys()))
    imported_dict.append(dict(kvs))

    processed_count+=1

text = "(" + str(processed_count) + "/" + str(len(folders)) + ") " + "processed"
status.config(text=text)
root.update()

# of all the keys in each inner folder, get common keys
flattened_list = [word for sublist in imported_keys for word in sublist]
word_set = set(flattened_list)
common_words = set.intersection(*map(set, imported_keys))

# create a dictionary out of the common keys and initialize its value to be [] for now
data = {key: [] for key in common_words}

# fill out the data to the dictionary
for dictionary in imported_dict:
    for key, value in dictionary.items():
        if key in data:
            clean_value = re.sub(r'^\s+|\s+$|,', "", value[0])  # remove leading, trailing, and extra commas
            data[key].append(clean_value.upper())               # append its uppercased value 

# create the dataframe    
pd.set_option('display.max_columns', None)                      # set no max columns to prevent df from being cut
df = pd.DataFrame(data)                                         # generate dataframe df

# display df in GUI's first frame
clear_data()
tv1["column"] = list(df.columns)                                # set the column names 
tv1["show"] = "headings"
for column in tv1["columns"]:                                   # display each headings
    tv1.heading(column, text=column)                            # let the column heading = column name
df_rows = df.to_numpy().tolist()                                # turns the dataframe into a list of lists
for row in df_rows:
    tv1.insert("", "end", values=row)

# display the visualization options elements 
visopt = Label(root, text="Choose variable: ")      # display prompt
visopt.place(rely=0.75, relx=0.05)
options = list(data.keys())                         # set the options as the headings
variable = StringVar(root)                          # set tracker of variable chosen by user
variable.set(options[0])                            # set default value
w = OptionMenu(root, variable, *options)            # display the option menu
w.place(rely=0.74, relx=0.22)
root.update()
button = Button(root, text="Click here to generate.", command=display_visualization)    # display button for displaying vis
button.place(rely=0.81, relx=0.05)

# save the data frame to a csv file and encrypt
filename = str(input_dir).split("/")[-1] + '.csv'
df.to_csv(filename, index=False)
encrypt_data(filename)

root.mainloop()

# References:
# AWS. (n.d). Extracting Key-Value Pairs from a Form Document. https://docs.aws.amazon.com/textract/latest/dg/examples-extract-kvp.html
# RamonWill (n.d).  View an excel file or Pandas Dataframe inside Tkinter. https://gist.github.com/RamonWill/0686bd8c793e2e755761a8f20a42c762
