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

image_path = "medkicklogo.png"
st.image(image_path, caption="", use_column_width=True)

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

    # Convert 'Start Time (local)' column to datetime format
    try:
        df['Start Time (local)'] = pd.to_datetime(df['Start Time (local)'], errors='coerce')
    except Exception as e:
        st.error(f"Error converting 'Start Time (local)' to datetime: {e}")

    # Convert 'Start Time (local)' column to datetime format
    df['Start Time (local)'] = pd.to_datetime(df['Start Time (local)'])

    # Function to extract call components based on direction
    def extract_call_components(row):
        if row['Direction'] == 'INBOUND':
            from_component = re.sub(r'\D', '', row['From'])
            to_component = re.sub(r'\D', '', row['To'])
        
        elif row['Direction'] == 'OUTBOUND':
            from_component = re.sub(r'\D', '', row['To'])
            to_component = re.sub(r'\D', '', row['From'])
        else:
            from_component = None
            to_component = None

        return from_component, to_component

    # Function to check if a nurse met the criteria for an inbound call
    def evaluate_performance(row):
        try:
            from_component, to_component = extract_call_components(row)
            if row['Direction'] == 'INBOUND':
                answer_time_str = row['Answer Time (local)']

                # Check if answer time is '--:--:--', treat as no answer
                if answer_time_str == '--:--:--':
                    duration = 0
                    from_number = re.sub(r'\D', '', row['From'])  # Extract only numeric part
                    to_number = re.sub(r'\D', '', row['To'])      # Extract only numeric part

                    # Check if the nurse answered the patient's call for at least 30 seconds
                    if row['Duration'] >= 30:
                        return f'Met criteria. Did not answer. Nurse called back at {row["Start Time (local)"]} to {from_number}. Answered for {row["Duration"]} seconds.'

                    # Look for an outbound call initiated by the nurse to the patient
                    call_back_row_nurse = df[(df['Direction'] == 'OUTBOUND') & 
                                       (df['To'].apply(lambda x: re.sub(r'\D', '', x)[-10:]) == from_number[-10:]) & 
                                       (df['From'].apply(lambda x: re.sub(r'\D', '', x)) == to_number) & 
                                       (row['Start Time (local)'] - pd.Timedelta(seconds=10) <= df['Start Time (local)']) & 
                                       (df['Start Time (local)'] <= row['Start Time (local)'] + pd.Timedelta(hours=1)) & 
                                       (df['Duration'] >= 1)].head(1)
                
                    # Look for an inbound call initiated by the patient to the nurse
                    call_back_row_patient = df[(df['Direction'] == 'INBOUND') & 
                                       (df['To'].apply(lambda x: re.sub(r'\D', '', x)[-10:]) == to_number) & 
                                       (df['From'].apply(lambda x: re.sub(r'\D', '', x)) == from_number[-10:]) & 
                                       (row['Start Time (local)'] - pd.Timedelta(seconds=10) <= df['Start Time (local)']) & 
                                       (df['Start Time (local)'] <= row['Start Time (local)'] + pd.Timedelta(hours=1)) & 
                                       (df['Duration'] >= 30)].head(1)
                
                    # Look for call backs > 1hr and < 10hr
                    call_back_nurse_1hr_10hr = df[(df['Direction'] == 'OUTBOUND') & 
                                                  (df['From'].apply(lambda x: re.sub(r'\D', '', x)) == to_number) &
                                                  (df['To'].apply(lambda x: re.sub(r'\D', '', x)[-10:]) == from_number[-10:]) &
                                                  (row['Start Time (local)'] + pd.Timedelta(hours=1) <= df['Start Time (local)']) &
                                                  (df['Start Time (local)'] <= row['Start Time (local)'] + pd.Timedelta(hours=10))]

                    call_back_patient_1hr_10hr = df[(df['Direction'] == 'INBOUND') &
                                                    (df['To'].apply(lambda x: re.sub(r'\D', '', x)[-10:]) == to_number) &
                                                    (df['From'].apply(lambda x: re.sub(r'\D', '', x)) == from_number[-10:]) &
                                                    (row['Start Time (local)'] + pd.Timedelta(hours=1) <= df['Start Time (local)']) &
                                                    (df['Start Time (local)'] <= row['Start Time (local)'] + pd.Timedelta(hours=10))]


                    if not call_back_row_nurse.empty:
                        # Ensure that the nurse called back and it's an outbound call
                        if call_back_row_nurse['Direction'].values[0] == 'OUTBOUND':
                            call_back_time = pd.to_datetime(call_back_row_nurse['Start Time (local)'].values[0]).tz_localize(None)
                            duration_call_back = call_back_row_nurse['Duration'].values[0]
                            return f'Met criteria. Did not answer. Nurse called back in 1hr. '
                        else:
                            return f'Did not answer. Nurse did not call back in 1hr.'
                    elif not call_back_row_patient.empty:
                        # Ensure that the patient called back and it's an inbound call
                        if call_back_row_patient['Direction'].values[0] == 'INBOUND':
                            call_back_time = pd.to_datetime(call_back_row_patient['Start Time (local)'].values[0]).tz_localize(None)
                            duration_call_back = call_back_row_patient['Duration'].values[0]
                            return f'Met criteria. Did not answer. Patient called back in 1hr.'
                        else:
                            return f'Did not answer. Nurse did not call back in 1hr.'
                    elif not call_back_nurse_1hr_10hr.empty:
                        # Ensure that the nurse called back and it's an outbound call
                        if call_back_nurse_1hr_10hr['Direction'].values[0] == 'OUTBOUND':
                            call_back_time = pd.to_datetime(call_back_nurse_1hr_10hr['Start Time (local)'].values[0]).tz_localize(None)
                            duration_call_back = call_back_nurse_1hr_10hr['Duration'].values[0]
                            return f'Did not Met criteria. Did not answer. Nurse called back in 10hr>&>1hr. '
                        else:
                            return f'Did not answer. Nurse did not call back in <10hr.'
                    elif not call_back_patient_1hr_10hr.empty:
                        # Ensure that the patient called back and it's an inbound call
                        if call_back_patient_1hr_10hr['Direction'].values[0] == 'INBOUND':
                            call_back_time = pd.to_datetime(call_back_patient_1hr_10hr['Start Time (local)'].values[0]).tz_localize(None)
                            duration_call_back = call_back_patient_1hr_10hr['Duration'].values[0]
                            return f'Did not Met criteria. Did not answer. Patient called back in 10hr>&>1hr.'
                        else:
                            return f'Did not answer. Nurse did not call back in <10hr.'
                    else:
                        return f'Did not answer. Nurse did not call back in 10hr.'
                
                answer_time = pd.to_datetime(answer_time_str).tz_localize(None)
                end_time = pd.to_datetime(row['End Time (local)']).tz_localize(None)
                duration = row['Duration']

                # Check if the call was answered for at least 30 seconds
                if duration >= 30:
                    return f'Met criteria. Answered for {duration} seconds.'

                else:
                    return f"Did not meet criteria. Received call at {answer_time} from {row['From']}."

            elif row['Direction'] == 'OUTBOUND':
                # You can add additional conditions for outbound calls if needed
                return 'Outbound call'

            else:
                return 'Not an inbound or outbound call'

        except Exception as e:
            return f"Error: {e}"

    # Streamlit App
    st.title('Nurse Phone Call Performance')

    # Convert 'Start Time (local)' column to datetime format
    df['Start Time (local)'] = pd.to_datetime(df['Start Time (local)'])

    # Sidebar for selecting performance criteria and date range
    performance_criteria = st.sidebar.selectbox('Select Performance Criteria', ['All', 'Answered', 'Missed','No Follow-up','Follow-up >1hr and <10hr','Follow-up <1hr'])

    # Allow selection of date range
    selected_from_date = st.sidebar.date_input('Select From Date', min_value=df['Start Time (local)'].min().date(), max_value=df['Start Time (local)'].max().date(), value=df['Start Time (local)'].min().date())
    selected_to_date = st.sidebar.date_input('Select To Date', min_value=df['Start Time (local)'].min().date(), max_value=df['Start Time (local)'].max().date(), value=df['Start Time (local)'].max().date())

    # Check if at least one date is selected
    if not selected_from_date or not selected_to_date:
        st.warning("Please select both 'From' and 'To' dates.")
    else:
        # Filter DataFrame based on selected date range
        filtered_df = df[(df['Start Time (local)'].dt.date >= selected_from_date) & (df['Start Time (local)'].dt.date <= selected_to_date)]

        # Apply the function to the filtered DataFrame
        filtered_df['Performance'] = filtered_df.apply(evaluate_performance, axis=1)

        # Count the number of calls that meet and do not meet the criteria
        met_criteria_count = len(filtered_df[filtered_df['Performance'].str.startswith('Met')])
        Answer_Call_count = len(filtered_df[filtered_df['Performance'].str.startswith('Met criteria. Answered')])
        Missed_Call_count = len(filtered_df[filtered_df['Performance'].str.startswith(('Met criteria. Did not answer.', 'Did not'))])
        Nurse_Call_Back_count = len(filtered_df[filtered_df['Performance'].str.startswith('Met criteria. Did not answer. Nurse called back')])
        Patient_Call_Back_count = len(filtered_df[filtered_df['Performance'].str.startswith('Met criteria. Did not answer. Patient called back')])
        did_not_meet_criteria_count = len(filtered_df[filtered_df['Performance'].str.startswith('Did not')])
        # Count the call-backs > 1hr and < 10hr
        call_back_nurse_1hr_10hr_count = len(filtered_df[filtered_df['Performance'].str.startswith('Did not Met criteria. Did not answer. Nurse called back')])
        call_back_patient_1hr_10hr_count = len(filtered_df[filtered_df['Performance'].str.startswith('Did not Met criteria. Did not answer. Patient called back')])

        # Count the number of inbound and outbound calls
        inbound_call_count = len(filtered_df[filtered_df['Direction'] == 'INBOUND'])
        outbound_call_count = len(filtered_df[filtered_df['Direction'] == 'OUTBOUND'])

        # Calculate the percentage of Good and Bad criteria
        total_criteria_count = met_criteria_count + did_not_meet_criteria_count

        # Avoid division by zero error
        if total_criteria_count > 0:
            good_percentage = (met_criteria_count / total_criteria_count) * 100
            bad_percentage = (did_not_meet_criteria_count / total_criteria_count) * 100
        else:
            good_percentage = 0
            bad_percentage = 0

        # Display the percentages
        st.markdown(f"<p style='color:green;font-size:24px;'>Good: <strong>{good_percentage:.2f}%</strong></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:red;font-size:24px;'>Bad: <strong>{bad_percentage:.2f}%</strong></p>", unsafe_allow_html=True)
        # Display the counts on top of the dashboard
        st.markdown(f"<p style='color:#5cb7a2;font-size:20px;'> Outbound Calls: <strong>{outbound_call_count}</strong></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#5cb7a2;font-size:20px;'> Inbound Calls: <strong>{inbound_call_count}</strong></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:green;font-size:20px;'> &nbsp;&nbsp;&nbsp;&nbsp;Answered calls: <strong>{Answer_Call_count}</strong></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:orange;font-size:20px;'> &nbsp;&nbsp;&nbsp;&nbsp;Missed calls: <strong>{Missed_Call_count}</strong></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:red;font-size:20px;'> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;No Follow-up: <strong>{did_not_meet_criteria_count}</strong></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:orange;font-size:20px;'> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Follow-up >1hr and <10hr: <strong>{call_back_nurse_1hr_10hr_count + call_back_patient_1hr_10hr_count}</strong></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:orange;font-size:18px;'> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;By Nurse: <strong>{call_back_nurse_1hr_10hr_count}</strong></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:orange;font-size:18px;'> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;By Patient: <strong>{call_back_patient_1hr_10hr_count}</strong></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#D8D800;font-size:20px;'> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Follow-up <1 hr: <strong>{Nurse_Call_Back_count + Patient_Call_Back_count}</strong></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#D8D800;font-size:18px;'> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;By Nurse: <strong>{Nurse_Call_Back_count}</strong></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#D8D800;font-size:18px;'> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;By Patient: <strong>{Patient_Call_Back_count}</strong></p>", unsafe_allow_html=True)
    
        # Display a bar chart
        st.subheader('Number of Calls Meeting Criteria')

        # Create a Plotly Express bar chart
        fig = px.bar(
            x=['Answered', 'Missed','Called Back in 1hr by Nurse','Called Back in 1hr by Patient','Did not call back in 1hr'],
            y=[Answer_Call_count, Missed_Call_count, Nurse_Call_Back_count, Patient_Call_Back_count, did_not_meet_criteria_count],
            text=[Answer_Call_count, Missed_Call_count, Nurse_Call_Back_count, Patient_Call_Back_count, did_not_meet_criteria_count],  # Display count values on top of the bars
            labels={'y': 'Count', 'x': 'Criteria'},
            color=['Answered', 'Missed','Called Back in 1hr by Nurse','Called Back in 1hr by Patient','Did not call back in 1hr'],
            color_discrete_map={'Answered': '#5cb7a2', 'Missed': '#74e5cb', 'Called Back in 1hr by Nurse': 'yellow', 'Called Back in 1hr by Patient': 'orange', 'Did not call back in 1hr': 'red'}
        )

        # Update layout to display text on top of the bars
        fig.update_traces(textposition='outside')

        # Display the Plotly Express chart using Streamlit
        st.plotly_chart(fig)

        # Display the evaluated performance based on selected criteria and dates
        st.subheader('Performance Evaluation Results')
        if performance_criteria == 'All':
            # Display only specific columns
            display_columns = ['From', 'To', 'Start Time (local)', 'Duration', 'Direction', 'Performance']
            st.write(filtered_df[display_columns])
        elif performance_criteria == 'Answered':
            # Display only specific columns
            display_columns = ['From', 'To', 'Start Time (local)', 'Duration', 'Direction', 'Performance']
            st.write(filtered_df[filtered_df['Performance'].str.startswith('Met criteria. Answered')][display_columns])
        elif performance_criteria == 'Missed':
            # Display only specific columns
            display_columns = ['From', 'To', 'Start Time (local)', 'Duration', 'Direction', 'Performance']
            st.write(filtered_df[filtered_df['Performance'].str.startswith('Met criteria. Did not answer.') | filtered_df['Performance'].str.startswith('Did not')])
        elif performance_criteria == 'No Follow-up':
            # Display only specific columns
            display_columns = ['From', 'To', 'Start Time (local)', 'Duration', 'Direction', 'Performance']
            st.write(filtered_df[filtered_df['Performance'].str.startswith('Did not')][display_columns])
        elif performance_criteria == 'Follow-up >1hr and <10hr':
            # Display only specific columns
            display_columns = ['From', 'To', 'Start Time (local)', 'Duration', 'Direction', 'Performance']
            st.write(filtered_df[filtered_df['Performance'].str.startswith('Did not Met criteria. Did not answer. Nurse called back') | filtered_df['Performance'].str.startswith('Did not Met criteria. Did not answer. Patient called back')])
        elif performance_criteria == 'Follow-up <1hr':
            # Display only specific columns
            display_columns = ['From', 'To', 'Start Time (local)', 'Duration', 'Direction', 'Performance']
            st.write(filtered_df[filtered_df['Performance'].str.startswith('Met criteria')][display_columns])
    
if __name__ == "__main__":
    main()