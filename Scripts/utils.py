import datetime
from datetime import date
import pandas as pd
import numpy as np
import requests
from pandas.tseries.offsets import BDay
from mip import Model, xsum, minimize, BINARY, maximize
import re

api_key = '30d9085988663142ce4cb478d09e6d00'


def next_weekday(d, weekday):
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0: 
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)


def get_calendar_df(event_df):
    next_monday = next_weekday(date.today(), 0) 

    upcoming_week_df = pd.DataFrame(index=pd.date_range(next_monday, periods=5, freq='D'))
    
    event_df = event_df.groupby('Datum').count()
    
    cal_df = upcoming_week_df.join(event_df).fillna(0).astype(int)
    
    return cal_df


def get_dates():
    today = pd.to_datetime('today')
    dates = [d.strftime('%Y-%m-%d') for d in pd.date_range(start=today+BDay(1), end=today + BDay(5))]
    return dates


def get_forecast_upcoming_week(cal_df, lat, lon):
    _, _, API_KEY = load_secrets()
    
    dates = get_dates()
    location = (lat, lon)
    
    url = f'https://api.openweathermap.org/data/2.5/onecall?lat={location[0]}&lon={location[1]}&exclude=current,minutely,hourly&appid={API_KEY}&units=metric'
    r = requests.get(url)
    
    # prepare df
    columns = ['date', 'temp_min', 'temp_max', 'temp_morning', 'temp_day',\
           'temp_evening', 'pressure', 'humidity', 'dew_point',\
           'wind_speed', 'pop', 'uvi']
    df_forecast = pd.DataFrame(columns=[columns])
    
    # loop through days
    for i, day in enumerate(r.json()['daily']):
        df_forecast.loc[i] = [day['dt'], day['temp']['min'], day['temp']['max'], \
                               day['temp']['morn'], day['temp']['day'], day['temp']['eve'], \
                               day['pressure'], day['humidity'], day['dew_point'], \
                               day['wind_speed'], day['pop'], day['uvi']]
    
    # data cleaning
    df_forecast.columns = columns
    df_forecast['date'] = df_forecast['date'].astype(str).str[:-2]
    df_forecast['date'] = pd.to_datetime(df_forecast['date'], unit='s')
    df_forecast['weekday'] = df_forecast['date'].dt.weekday < 5

    df_forecast = df_forecast.loc[df_forecast['weekday']==True]
    df_forecast['date'] = df_forecast['date'].dt.strftime("%Y-%m-%d")
    df_forecast.index = cal_df.index 
    df_forecast = df_forecast.drop('date', axis=1)
    
    return df_forecast


def get_mobility_data(cal_df):
    """
    TODO: international possible default here Germany
    """
    
    dates = get_dates()
    
    url = f'https://covid19-static.cdn-apple.com/covid19-mobility-data/2019HotfixDev24/v3/en-us/applemobilitytrends-2020-10-29.csv'
    df_mobility = pd.read_csv(url)
    
    map_df = df_mobility[df_mobility['region'] == "Germany"].T[6:].rename(columns={45: "driving", 46: "transit", 47: "walking"})
    map_df.index = pd.to_datetime(map_df.index)
    map_df = map_df.loc[(map_df.index >= '2020-10-19') & (map_df.index <= '2020-10-23')]
    map_df.index = cal_df.index
    return map_df


def merge_data_create_model(df):
    df = df.copy()
    for col in df.columns:
        # if col=='appointments':
        #    continue

        
        if col in ['driving', 'transit', 'wind_speed', 'pop']:
            # if values are high I like to stay at home thus inverting
            df[col] = -1*df[col] 
        elif col=='temp_day' or col=='humidity':
            # stay at home if differ from mean
            df[col] = -1*(df[col] - df[col].mean()).abs()
        
        df[col]=(df[col]-df[col].min())/(df[col].max()-df[col].min())

    y = df.sum(axis=1).to_numpy()
    return y, df


def get_world_data():
    df_cities = pd.read_csv('../Data/worldcities.csv')
    df_cities = df_cities.loc[df_cities['country'] == 'Germany', ['city', 'lat', 'lng']]
    df_cities = df_cities.reset_index(drop=True)
    return df_cities.sort_values(by="city").copy()


def mip_optimization(cal_df, y, constrain=3, daily_weights=None):
    """Mixed integer linear programming optimization with constraints.
    Args:
        y (numpy.ndarray): sum of daily features (dim=#ofdays)
        constrain (int): minimum days in office
        daily_weights (array): weighting of days, e.g. if you prefer to come on mondays
    Return:
         
    """
    # daily weighting
    u = np.ones(len(y)) if daily_weights==None else daily_weights
    I = range(len(y))   # idx for days for summation

    m = Model("knapsack")   # MIP model
    w = [m.add_var(var_type=BINARY) for i in I] # weights to optimize
    m.objective  = maximize(xsum(y[i]* w[i] for i in I)) # optimization function
    m += xsum(w[i] * u[i] for i in I) <= constrain # constraint 
    m.optimize()

    #selected = [i for i in I if w[i].x >= 0.99]
    selected = [w[i].x for i in I]
    
    df = pd.DataFrame(columns=["home_office"], index=cal_df.index, data={'home_office': selected})
    
    return df


def load_secrets():
    secrets = open('../Auth/secrets.txt', 'r') 
    CALENDAR_ID = secrets.readline()
    IFRAME = secrets.readline()
    API_KEY = secrets.readline()
    
    CALENDAR_ID = re.findall(r'"[^"]*"',CALENDAR_ID)[0].strip()[1:-1]
    IFRAME = re.findall(r'"[^"]*"',IFRAME)[0].strip()[1:-1]
    API_KEY = re.findall(r'"[^"]*"',API_KEY)[0].strip()[1:-1]

    secrets.close()
    return CALENDAR_ID, IFRAME, API_KEY