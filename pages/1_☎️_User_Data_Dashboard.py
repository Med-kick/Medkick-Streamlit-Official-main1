import streamlit as st
import pandas as pd
import datetime 
import re
import numpy as np

# import StringIO
from io import StringIO

st.title("Medkick User Data Dashboard")

# import Get Nurse List
from AWSSupport import GetNurseListFromServer, GetAllCsvDataFromS3


def CleanDataInput(df):
    try:
        # convert the From Number and To Number to string
        df["From"] = df["From"].astype(str)
        df["To"] = df["To"].astype(str)
        
        # Your previous data cleaning steps
        df = df.drop(['Start Time (local)', 'Answer Time (local)', 'End Time (local)'], axis=1)
        df["Start Time"] = pd.to_datetime(df["Start Time"], errors="coerce")
        df["Answer Time"] = pd.to_datetime(df["Answer Time"], errors="coerce")
        df["End Time"] = pd.to_datetime(df["End Time"], errors="coerce")
        df["Duration"] = df["Duration"].astype(int)
        df["Disposition"] = df["Disposition"].astype(int)
        df["From Number"] = df["From"].apply(lambda x: re.findall(r"\((\d+)\)", x)[0] if re.findall(r"\((\d+)\)", x) else np.nan)
        df["To Number"] = df["To"].apply(lambda x: re.findall(r"\((\d+)\)", x)[0] if re.findall(r"\((\d+)\)", x) else np.nan)
        df["Start Time (rounded)"] = df["Start Time"].dt.round("min")
        df = df[["From", "From Number", "To", 'To Number', "Start Time", "Start Time (rounded)", "Answer Time", "End Time", "Duration", "Disposition", "Direction"]]
        df = df.drop_duplicates(subset=["From", "Start Time (rounded)"], keep="first")
        df = df.sort_values(by="Start Time").reset_index(drop=True)

        return df
    except Exception as e:
        print(e)
        # streamlit error
        st.error(f"An error occurred: {str(e)}")


# get the df_missed table
def get_missed_table(df, window_duration):
    df_missed = df[(df['Direction'] == 'INBOUND') & (df['Duration'] == 0)]
    
    window_duration = datetime.timedelta(hours=window_duration)

    # okay, vs mỗi cái missed call này
    df_missed['not_call_back'] = 'Yes'
    df_missed['start_search_window'] = df_missed['End Time']
    df_missed['end_search_window'] = df_missed['End Time'] + window_duration
    return df_missed

# filter all the missed call that has not been called back
def not_call_back_filter(df, df_missed):
    
    for index, row in df_missed.iterrows():
        from_number = row["From Number"]
        to_number = row["To"]
        end_time = row["End Time"]
        start_time_window = row["start_search_window"]
        end_time_window = row["end_search_window"]

        # okay, h nếu như cái From match cái to, tức là gọi ngược về
        matching_rows = df[
            (df["From"] == to_number)
            & (df["To"] == from_number)
            & (df["Start Time"] >= start_time_window)
            & (df["Start Time"] <= end_time_window)
        ]

        # if the matchings rows is empty, then there is no call back within 1 hour
        if matching_rows.empty:
            df_missed.loc[index, "not_call_back"] = "Yes"
        else:
            df_missed.loc[index, "not_call_back"] = "No"    
            
    return df_missed
        
# count the missed call
def count_missed_call(df_missed):
    total_missed_call = df_missed.shape[0]
    
    # the total of not call back
    total_not_call_back = df_missed[df_missed['not_call_back'] == 'Yes'].shape[0]
    
    # the total of call back
    total_call_back = df_missed[df_missed['not_call_back'] == 'No'].shape[0]
    
    return total_missed_call, total_not_call_back, total_call_back
        
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

# cache the data
@st.cache_data
def get_all_csv_data():
    all_csv = GetAllCsvDataFromS3()
    print('this is all data', all_csv)

    # check if the all_csv is a valid dictionary
    if isinstance(all_csv, dict):
        for key, value in all_csv.items():
            # Check if the key is a string and the value is a DataFrame
            if isinstance(key, str) and isinstance(value, pd.DataFrame):
                print(f"Valid data: {key}")
            else:
                print(f"Invalid data: {key}")

    # loop over the all_csv and clean the data
    for key, df in all_csv.items():
        print('Processing:', key)
        try:
            # Since df is already a DataFrame, no need to read it again
            cleaned_df = CleanDataInput(df)
            all_csv[key] = cleaned_df
        except Exception as e:
            print(e)
            # streamlit error
            st.error(f"An error occurred: {str(e)}")

    return all_csv
                
def main():

    try:
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
        
        
        # display df
        st.write(df)
        
        # the amount of time for the window
        window_duration = st.slider(label="Select the window duration", min_value=1, max_value=24, step=1, value=1, format="%d hours")
        st.write(f"Window duration: {window_duration} hours")
        
        # create the missed df
        df_missed = get_missed_table(df=df, window_duration=window_duration)
        
        # now get all the missed call that has not been called back
        df_missed = not_call_back_filter(df=df, df_missed=df_missed)
            
        # okay, so now get the total number of phone call 
        total_phone_call = df.shape[0]
        
        # the total of INBOUND phone call
        total_inbound = df[df['Direction'] == 'INBOUND'].shape[0]
        
        # the total of OUTBOUND phone call
        total_outbound = df[df['Direction'] == 'OUTBOUND'].shape[0]
    
        
        # create 3 metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Phone Calls", str(total_phone_call))
        col2.metric("Total Inbound Calls ", str(total_inbound))
        col3.metric("Total Outbound Calls", str(total_outbound))
            
        # now get the missed call
        total_missed_call, total_not_call_back, total_call_back = count_missed_call(df_missed=df_missed)
        
        # add a streamlit divider
        
        # create 3 metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Missed Calls", str(total_missed_call))
        col2.metric("Total Not Call Back ", str(total_not_call_back))
        col3.metric("Total Call Back", str(total_call_back))
    except:
        st.error("An error occurred for this nurse")  
    
if __name__ == "__main__":
    main()