import pandas as pd
import numpy as np
from PIL import Image

import streamlit as st
import streamlit.components.v1 as components
from mip import Model, xsum, minimize, BINARY, maximize
import time

from utils import *
from calendar_api import *

_, IFRAME, _ = load_secrets()

#Web App        
service = cal_service_builder()
cal_events = get_n_calendar_events(100, service)


## DataFrames
schedule_df = pd.read_csv("../Data/schedule_df.csv")
cal_df = get_calendar_df(cal_events)
world_df = get_world_data()

st.header('Climate Change Hackathon')
st.title('Make Homeoffice Great Again')
    
st.write('')

st.sidebar.title("Our Team")
st.sidebar.header("Rescue the World with us")
st.sidebar.write('')
    
image = Image.open('../Images/jakob.jpeg')
st.sidebar.image(image, caption='Jakob Schlör', width=200, height=200)

image = Image.open('../Images/tim.jpg')
st.sidebar.image(image, caption='Tim Löhr', width=200)

image = Image.open('../Images/yasin.jpeg')
st.sidebar.image(image, caption='Yasin Edin', width=200)

image = Image.open('../Images/timo.jpeg')
st.sidebar.image(image, caption='Timo Bohnstedt', width=200)

location = st.selectbox("Select your city: ", world_df['city'].reset_index(drop=True))
st.write('') 

lat = world_df[world_df['city'] == location]['lat'].values[0]
lon = world_df[world_df['city'] == location]['lng'].values[0]

forecast_df = get_forecast_upcoming_week(cal_df, lat, lon)
mobility_df = get_mobility_data(cal_df)

df_merged = pd.concat([cal_df, mobility_df, forecast_df], axis=1)

colums = ["Termin", "driving", "transit", "temp_day",	"humidity", "wind_speed", "pop", "uvi"]
df_merged = df_merged[colums]

button = st.button("Create Schedule for the next week")

if not button:
    st.write('')
    st.write('')
    image = Image.open('../Images/background.png')
    st.image(image, width=700)

if button:    
    if schedule_df[schedule_df['Week'] == get_dates()[0]]['Scheduled'].values[0] == False:
        st.write('') 
        
        y, df_week = merge_data_create_model(df_merged)
        
        with st.spinner('In Progress...'): 
            event_df = mip_optimization(cal_df, y, constrain=2)

        events = cal_event_creator(event_df, location)
        
        for event in events:
            cal_event_dispatcher(service, event)
        
        st.success('Schedule successfully created! - Thank you')
        schedule_df.loc[schedule_df['Week'] == get_dates()[0], ['Scheduled']] = True
        schedule_df.to_csv("../Data/schedule_df.csv", index=False)
    

    else:
        st.warning("Schedule for the upcoming week has already been prepared.")   
        
    
    num_week = 24
    st.write('')
    my_bar = st.progress(0)
    for num_weeks in range(num_week):
        co2_reduction_app_max_year = 3.2e9*1.5 # greenpeace
        co2_worker_week = co2_reduction_app_max_year/(50*11e6)
        tree_per_year = 15.7
        trees = co2_worker_week/tree_per_year 
        max_trees = trees*50
        progress = 1/50 * (num_weeks +1)
        my_bar.progress(progress)  
        time.sleep(0.05)
        
    st.write('So far you have planted {:.1f} out of max {:.1f} trees per year!'.format(trees*num_weeks, max_trees))         
    st.write('')

        
    components.iframe(f"{IFRAME}", height=600, scrolling=True)
    st.write('')
    st.header('Each week you plant {:.1f} trees!'.format(trees))
    st.balloons()    
    