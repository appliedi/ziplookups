
#         engine = create_engine('postgresql://postgres:Appliedi1234@ezpanel02.qitsolutions.com:5432/zipcodes')
 
import streamlit as st
import pandas as pd
import pydeck as pdk
from sqlalchemy import create_engine
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import geopandas as gpd
from shapely.geometry import Point

# Convert miles to kilometers
def convert_miles_to_km(miles):
    return miles * 1.60934

# Initialize geolocator with a unique user-agent
geolocator = Nominatim(user_agent="streamlitAppLocationRadius")
geocode_with_rate_limiter = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def get_npi_records_within_radius(engine, lat, lon, radius_km):
    query = """
    SELECT nr.npi AS "NPI", nr.*, g.latitude AS "Latitude", g.longitude AS "Longitude"
    FROM npi_registry AS nr
    JOIN (
        SELECT npi, latitude, longitude
        FROM geocoded
        WHERE (
            6371 * acos (
                cos(radians(%s))
                * cos(radians(latitude))
                * cos(radians(longitude) - radians(%s))
                + sin(radians(%s)) * sin(radians(latitude))
            )
        ) <= %s
    ) AS g ON nr.npi = g.npi
    WHERE (nr."NPI Deactivation Date" IS NULL OR 
           (nr."NPI Reactivation Date" IS NOT NULL AND nr."NPI Reactivation Date" > nr."NPI Deactivation Date"));
    """
    return pd.read_sql_query(query, engine, params=(lat, lon, lat, radius_km))




def create_circle_polygon(latitude, longitude, radius_in_km, num_vertices=64):
    center = Point([longitude, latitude])
    circle = center.buffer(radius_in_km / 111.32)  # Earth's radius in kilometers = 111.32 km per degree
    return gpd.GeoSeries([circle]).__geo_interface__

st.title("Location and Radius Visualizer")

address_input = st.text_input("Enter an address")
radius_input = st.slider("Radius (miles)", min_value=1, max_value=100, value=10)

if address_input:
    location = geocode_with_rate_limiter(address_input)
    if location:
        # Update the connection string below with your actual PostgreSQL connection details
        engine = create_engine('postgresql://postgres:Appliedi1234@ezpanel02.qitsolutions.com:5432/zipcodes')
        radius_km = convert_miles_to_km(radius_input)

        # Fetch latitude and longitude for plotting
        preliminary_data = get_npi_records_within_radius(engine, location.latitude, location.longitude, radius_km)[['NPI', 'Latitude', 'Longitude']]

        circle_geojson = create_circle_polygon(location.latitude, location.longitude, radius_km)
        
        # Plot the initial points on the map
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(
                latitude=location.latitude,
                longitude=location.longitude,
                zoom=11,
                pitch=50,
            ),
            layers=[
                pdk.Layer(
                    "GeoJsonLayer",
                    data=circle_geojson,
                    opacity=0.5,
                    stroke=True,
                    fill=True,
                    get_line_color=[255, 0, 0],
                    get_fill_color=[255, 180, 0, 140],
                    get_line_width=2,
                    line_width_min_pixels=1,
                ),
                pdk.Layer(
                    "ScatterplotLayer",
                    data=preliminary_data,
                    get_position='[Longitude, Latitude]',
                    get_color='[0, 30, 200, 160]',
                    get_radius=100,
                ),
            ]
        ))

        if st.button("Pull Records"):
            # Fetch and display detailed records only after the button is pressed
            detailed_records = get_npi_records_within_radius(engine, location.latitude, location.longitude, radius_km)
            st.dataframe(detailed_records.drop(columns=['Latitude', 'Longitude']))  # Exclude columns if they're not needed for the detailed view
        else:
            st.write("Click the 'Pull Records' button to fetch detailed information for the displayed points.")
    else:
        st.error("Address not found. Please try a different one.")
