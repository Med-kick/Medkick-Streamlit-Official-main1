import streamlit as st
import pandas as pd
import re
import numpy as np
from datetime import datetime, timedelta
from st_files_connection import FilesConnection
import plotly.express as px

# import StringIO
from io import StringIO

st.title("Medkick User Data Dashboard")

# import Get Nurse List
from AWSSupport import GetNurseListFromServer, GetAllCsvDataFromS3


def CleanDataInput(df):

    return df
        
def get_nurse_data(nurse_name):
    st.toast(f"Loading data for {nurse_name}...", icon="⏳") 
    
    all_csv = get_all_csv_data()
        
    # the nurse name is the key
    nurse_key = f"{nurse_name}.csv"
    
    # log them out
    nurse_df = all_csv[nurse_key]
    return nurse_df
    
    # load data

# get all data
@st.cache_data
def get_all_csv_data():
    all_csv = GetAllCsvDataFromS3()
        
    # loop over the all_csv and clean the data
    for key, value in all_csv.items():
        all_csv[key] = CleanDataInput(value)
        
    return all_csv
                
def main():

        
    # load data
    with st.sidebar:
        st.write("## Currently Tracked Nurses")  

        # load the nurse list
        nurse_df = GetNurseListFromServer()
        
        if 'nurse_name' not in st.session_state:
            nurse_name = nurse_df['Name'].values[0]
            # add to session state
            st.session_state['nurse_name'] = nurse_name
            
        for i in nurse_df['Name'].values:
            nurse_name = st.button(label=i, key=i, use_container_width=True, on_click=get_nurse_data, args=[i])
            
            # if the nurse_name is clicked, then update the session state
            if nurse_name:
                st.session_state['nurse_name'] = i
            
    
    nurse_name = st.session_state['nurse_name']
    df = get_nurse_data(nurse_name=nurse_name)    
    
    df = pd.DataFrame(df)

    # Read only the first 300 rows
    df = df.head(1000)

    print(df.columns)

    
    
if __name__ == "__main__":
    main()