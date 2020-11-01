import pandas as pd
import numpy as np

import datetime
from datetime import date
import pickle
import os.path

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import streamlit as st
import streamlit.components.v1 as components

from utils import *

CREDENTIALS_PATH = '../Auth/credentials.json'
TOKEN_PICKLE_PATH = '../Auth/token.pickle'
CALENDAR_ID, _, _ = load_secrets()


def get_n_calendar_events(n, service):
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    
    events_result = service.events().list(calendarId=CALENDAR_ID, timeMin=now,
                                        maxResults=10, singleEvents=True,
                                        orderBy='startTime').execute()
    
    events = events_result.get('items', [])
    
    df = pd.DataFrame(columns=["Datum", "Termin"])
        
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        event = event['summary']
        
        df = df.append({"Datum": start[:10], "Termin":  event}, ignore_index=True)     

    df['Datum'] = pd.to_datetime(df['Datum'])
    df = df.set_index('Datum')
        
    return df



def cal_service_builder():
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_PICKLE_PATH):
        with open(TOKEN_PICKLE_PATH, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_PICKLE_PATH, 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service



def cal_event_dispatcher(service, event):
    event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    print('Event created: %s' % (event.get('htmlLink')))
    
    
def cal_event_creator(event_df, location):
    event_summary = ['Homeoffice - Stay at Home','Go to Company']
    event_color = [1, 2]
    events = []

    for (i, row) in event_df.iterrows():
        event = {
            'summary': event_summary[int(row['home_office'])],
            'colorId': event_color[int(row['home_office'])],
            'location': location,
            'description': 'We take the climate challenge',
            'start': {
            'dateTime': str(i.date()) + 'T08:00:00-00:00'
            },
            'end': {
                'dateTime': str(i.date()) + 'T16:00:00-00:00'
            }}
            
        events.append(event)
        
    return events