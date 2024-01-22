import pandas as pd
import numpy as np
import boto3
from io import StringIO
import re

BUCKET_NAME = "call-report-user-activity"

# AWS credentials
AWS_KEY= 'AKIAZNQI3UZBGYICQ7DF'
AWS_SECRET='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'

# Support file
NURSE_LIST_FILE_NAME = 'NursesList.csv'

# Clean data

def GetAllCsvDataFromS3():
    s3_client = boto3.client('s3', aws_access_key_id=AWS_KEY, aws_secret_access_key=AWS_SECRET)
    
    # List all objects within the S3 bucket
    objects = s3_client.list_objects_v2(Bucket=BUCKET_NAME)

    # Initialize an empty dictionary to hold data
    data_dict = {}

    # Loop through each object, if the file is a CSV, read it into a DataFrame
    for obj in objects.get('Contents', []):
        file_name = obj['Key']
        if file_name.endswith('.csv') and 'NursesList' not in file_name:  # Only process CSV files and exclude NursesName
            response = s3_client.get_object(Bucket=BUCKET_NAME, Key=file_name)
            df = pd.read_csv(response['Body'])   
            
            # Add the DataFrame to the dictionary        
            data_dict[file_name] = df
            print('Added', file_name, 'to data_dict')
            
    # this is to signify when they run the get data multiple times
    
    return data_dict

# updated the list of nurses to the server
def UpdateNurseListToServer(nurse_list_df):
    try:
        # Initialize S3 resource
        s3_resource = boto3.resource('s3', aws_access_key_id=AWS_KEY, aws_secret_access_key=AWS_SECRET)
        s3_client = boto3.client('s3', aws_access_key_id=AWS_KEY, aws_secret_access_key=AWS_SECRET)
        
        # Get the existing data from the server
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=NURSE_LIST_FILE_NAME)
        existing_data = pd.read_csv(obj['Body'])
        
        # Append new data
        updated_data = pd.concat([existing_data, nurse_list_df], ignore_index=True)
        
        # Convert the updated DataFrame to csv
        csv_buffer = StringIO()
        updated_data.to_csv(csv_buffer, index=False)
        
        # Upload the updated csv to the server
        s3_resource.Object(BUCKET_NAME, NURSE_LIST_FILE_NAME).put(Body=csv_buffer.getvalue())
        
        return 'Success'
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return 'Failed'
    
    
# Get the list of nurses from the server
def GetNurseListFromServer():
    try:
        # get the file from the server
        s3_client = boto3.client('s3', aws_access_key_id=AWS_KEY, aws_secret_access_key=AWS_SECRET)
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=NURSE_LIST_FILE_NAME)
        
        # read the csv file
        df = pd.read_csv(response['Body'])
        
        return df
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

# Remove the nurse from the server
def RemoveNurseFromServer(nurse_list_df):
    try:
        # convert the dataframe to csv
        csv_buffer = StringIO()
        nurse_list_df.to_csv(csv_buffer, index=False)
        
        # upload the csv to the server
        s3_resource = boto3.resource('s3', aws_access_key_id=AWS_KEY, aws_secret_access_key=AWS_SECRET)
        s3_resource.Object(BUCKET_NAME, NURSE_LIST_FILE_NAME).put(Body=csv_buffer.getvalue())
        
        return 'Success'
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return 'Failed'
