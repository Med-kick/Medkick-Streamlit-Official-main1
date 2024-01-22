import streamlit as st
import pandas as pd
import os
import time

# support files
import AWSSupport as aws_support

# File path for the CSV file to store submissions
CSV_FILE = 'submissions.csv'


# Get data from S3
def GetNurseList():
    nurse_list_df = aws_support.GetNurseListFromServer()
    
    return nurse_list_df


# If CSV does not exist, create it with initial columns
if not os.path.isfile(CSV_FILE):
    pd.DataFrame(columns=['Name', 'Link']).to_csv(CSV_FILE, index=False)

# Load existing data
data = pd.read_csv(CSV_FILE)

# Streamlit User Interface

st.title("Adding Nurses to the Database")

# Current nurses in the database
current_nurse_df = aws_support.GetNurseListFromServer()
st.write('There are currently ',(current_nurse_df.shape[0]),' nurses in the database')
st.dataframe(current_nurse_df, width=1200)

# instructions to add nurses
with st.expander("Instructions to add nurses"):
    
    st.write('''You can add new nurses by entering their name and link to their user activity. Below is how to get user activity link:  ''')
             
    st.write('*1. Go to the user activity page*')
    st.image("./images/user-activity.png")

    st.write('*2. Go to the nurse you want*')
    st.image("./images/user-activity-username-circle.png")
    
    st.write('*3. Get the link*')
    st.image("./images/user-activity-profile-link.png")

           
st.subheader("Add New Nurse Form" )
with st.form("my_form"):
    name = st.text_input("Name")

    link = st.text_input("Link")
    submitted = st.form_submit_button("Add",    )

    if submitted and name and link:  # Check if form is submitted and values are provided
        
          # format the name
        # strip leading and trailing spaces
        name = name.strip()
        
        # split the name into parts
        name_parts = name.split()
        name = '_'.join([part.capitalize() for part in name_parts])
        
          # format the link
        # strip leading and trailing spaces
        link = link.strip()

        # Append new data to DataFrame and save to CSV
        new_data = pd.DataFrame([[name, link]], columns=['Name', 'Link'])
        data = pd.concat([data, new_data], ignore_index=True)
        data.to_csv(CSV_FILE, index=False)
    else:
        st.toast('Please enter something!', icon='😍')

        

# Display the DataFrame on the page
st.write("Submitted Data:")
st.info('You can delete rows from this table. Please refer to the instruction below ', icon="ℹ️")
edited_df = st.data_editor(data, width=1200, num_rows='dynamic')

# write edited_df to csv

with st.expander("❓Data Editor Table Instructions"):
    st.write('Please refer to this video: https://youtu.be/6tah69LkfxE?list=TLGGKK4Dnf1gepcwMjAxMjAyNA&t=23')

edited_df.to_csv(CSV_FILE, index=False)

# button to Submit data to server
submit_data = st.button("Submit Data", key='add nurse')

if submit_data:
    
    # if the data is empty show warning
    if edited_df.empty:
        st.warning("No Data to Submit")
    else:
        try:
            # remove all empty rows 
            edited_df = edited_df.dropna(how='all')
            
            st.write("Data Submitted")
            st.dataframe(edited_df, width=1200)
            status = aws_support.UpdateNurseListToServer(edited_df)
            
            if status == "Success":
                st.success('Data submitted successfully')
                
                time.sleep(3)
                
                # remove the submissions.csv file
                os.remove(CSV_FILE)
                
                # rerun the page
                st.rerun()
            else:
                st.error('Data failed to submit')
                st.stop()
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.stop()




