import streamlit as st
from uszipcode import SearchEngine
import sqlite3
import pandas as pd

def get_zipcodes_within_radius(base_zipcode, radius_miles):
    search = SearchEngine()
    base_zip = search.by_zipcode(base_zipcode)
    if not base_zip.zipcode:
        return None, f"Zipcode {base_zipcode} not found."
    
    results = search.by_coordinates(base_zip.lat, base_zip.lng, radius=radius_miles, returns=0)
    zipcodes = [result.zipcode for result in results]
    return zipcodes, ""

def find_npi_records(zip_codes):
    conn = sqlite3.connect('ue3doctors_db.sqlite3')  # Update this path as necessary
    cursor = conn.cursor()
    
    query_parts = [f'"{zip_code}%"' for zip_code in zip_codes]
    zip_condition = " OR ".join([f'"Provider Business Practice Location Address Postal Code" LIKE {part}' for part in query_parts])
    
    # Exclude specific "Provider Credential Text"
    credentials_to_exclude = ['AU', 'CNA', 'CP', 'CSW', 'DC', 'PT']
    credential_conditions = " AND ".join([f'\"Provider Credential Text\" NOT LIKE \'%{credential}%\'' for credential in credentials_to_exclude])
    
    sql_query = f"SELECT * FROM npi_registry WHERE ({zip_condition}) AND \"Entity Type Code\" <> '2' AND ({credential_conditions});"
    
    cursor.execute(sql_query)
    rows = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    conn.close()
    df = pd.DataFrame(rows, columns=columns)
    return df

# Streamlit UI setup
st.title('NPI Registry Search by Zipcode Radius')

base_zipcode = st.text_input("Enter a zipcode:")
radius_miles = st.number_input("Enter radius in miles:", min_value=1, max_value=100, value=50)

if st.button('Search NPI Registry'):
    zip_codes, message = get_zipcodes_within_radius(base_zipcode, radius_miles)
    if zip_codes:
        st.success(f"Searching NPI Registry for records within {radius_miles} miles of {base_zipcode}, Entity Type Code not equal to 2, and excluding specific credentials...")
        df = find_npi_records(zip_codes)
        if not df.empty:
            st.session_state['df'] = df  # Store the initial search results
            st.dataframe(df)  # Display the dataframe
        else:
            st.info("No NPI records found within the specified radius or filters.")
    else:
        st.error(message)

# Secondary search for last name, if initial results exist
if 'df' in st.session_state and not st.session_state['df'].empty:
    provider_last_name = st.text_input("Enter Provider Last Name (Legal Name):")
    if st.button('Find by Last Name'):
        filtered_df = st.session_state['df'][st.session_state['df']['Provider Last Name (Legal Name)'].str.contains(provider_last_name, case=False, na=False)]
        if not filtered_df.empty:
            st.write(f"Found {len(filtered_df)} records matching the last name '{provider_last_name}':")
            st.dataframe(filtered_df)
        else:
            st.info(f"No records found for last name '{provider_last_name}'.")
