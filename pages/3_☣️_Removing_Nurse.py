
import streamlit as st
import pandas as pd

# support files
import AWSSupport as aws_support


# Get data from S3
def GetNurseList():
    nurse_list_df = aws_support.GetNurseListFromServer()
    
    return nurse_list_df

st.title("Removing Nurses from the Database")

# write the list of nurses
with st.expander("☄️Instructions to remove nurses"):
    st.write('''Below is the list of nurses in the database, to remove them, please refer to this video: https://youtu.be/6tah69LkfxE?list=TLGGKK4Dnf1gepcwMjAxMjAyNA&t=23 ''')
    
    st.write('After remove all the nurses from the database, please click the button below to submit the data to the server. The current data will be saved to the server and will be used for the next time the scraper run.')
    
# a button to fetch the data again
fetch_data = st.button("Fetch Data Again", key='fetch data')

if fetch_data:
    # rerun     
    st.rerun()

# get the list of nurses from the data_dict
nurse_list_df = GetNurseList()
if nurse_list_df is None:
    st.error('Failed to get the list of nurses from the server')
    st.stop()
    
st.write('There are currently ',(nurse_list_df.shape[0]),' nurses in the database')
updated_nurses_df = st.data_editor(nurse_list_df, width=1200, num_rows='dynamic', key='second data editor') # key is used to make sure the data editor is not duplicated
 
# a button to submit the data
submit_data = st.button("Submit Data", key='submit data updated nurse table')

if submit_data:
    # if the len is the same
    if len(updated_nurses_df) != len(nurse_list_df):
        
        status = aws_support.RemoveNurseFromServer(updated_nurses_df)
        if status == 'Success':
            st.success('Data submitted successfully')
        else: 
            st.error('Data failed to submit')
        
    else:
        st.toast('You have not made any updated', icon='🤔')