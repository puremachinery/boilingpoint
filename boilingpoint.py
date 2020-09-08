import configparser
import datetime
import json
import os
import requests
from twilio.rest import Client

config_file = 'scorched.ini'
weather_uri = 'api.weather.gov'
aqi_uri ='api.waqi.info'
sent_ev = 'WEATHER_NOTIFICATION_SENT'

already_sent = os.environ.get(sent_ev)
current_time = datetime.datetime.now()

# cron this every day at 2pm

# If it's a new day, reset the already_sent environment variable to today:
if already_sent and current_time.day > already_sent:
    os.environ[sent_ev] = current_time.day
elif current_time.hour > 13:
    config = configparser.ConfigParser()
    config.read(config_file)

    latlong = config[weather_uri]['latlong']
    forecast_hourly_endpoint = requests.get(f'{weather_uri}/points/{latlong}')['forecastHourly']
    weather_response = requests.get(forecast_hourly_endpoint)
    periods = weather_response['properties']['periods']
    temperature_now = int(periods[0]['temperature'])
    temperature_next_hour = int(periods[1]['temperature'])
    # check if temperature is expected to drop in an hour
    if temperature_next_hour <= temperature_now:
        city = config[aqi_uri]['city']
        aqi_token = config[aqi_uri]['token']
        aqi_response = requests.get(f'{aqi_uri}/feed/{city}/?token={aqi_token}')
        aqi_data = aqi_response['data']['forecast']['daily']['pm10'][0]
        aqi_avg = aqi_data['avg']
        aqi_day = aqi_data['day']

        # send a notification about dropping temperatures if one hasn't been sent yet today
        twilio_account_sid = config['twilio']['account_sid']
        twilio_auth_token = config['twilio']['auth_token']
        twilio_number = config['twilio']['from_number']
        to_number = config['twilio']['to_number']
        client = Client(twilio_account_sid, twilio_auth_token)

        message = client.messages \
            .create(
                body=f'It\'s getting colder! Average AQI is {aqi_avg} for {aqi_day}.',
                from_=twilio_number,
                to=to_number
            )

        os.environ[sent_ev] = current_time.day
