# Week 2: Forms and API Exploration
# Author: Coleen Therese A. Agsao

from decouple import config     # for .env
import boto3                    # for aws client
import os

directory = 'images'
images = []

for filename in os.listdir(directory):
    f = os.path.join(directory, filename)
    if os.path.isfile(f):
        images.append(f)    # put the filenames into a list

# save aws_access_key_id and aws_secret_access_key from .env
key_id = config('aws_access_key_id', default='')
access_key = config('aws_secret_access_key', default='')

# define client for textract
client = boto3.client('textract', region_name='us-east-1',aws_access_key_id=key_id, aws_secret_access_key=access_key)

for i, image in enumerate(images):
    if i == 0:
        with open(image, 'rb') as image:
            img = bytearray(image.read())

        print("[ONGOING] " + images[i])
        response = client.detect_document_text(Document = {'Bytes': img})
        
        text = ""

        for item in response["Blocks"]:
            if item["BlockType"] == "LINE":
                print(item["Text"])
                text = text + " " + item["Text"]

    
    
    

    
    


