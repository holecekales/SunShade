#!/usr/bin/env python3
from astral import LocationInfo
from astral.sun import elevation, azimuth #, sun
from datetime import datetime
import requests
from math import degrees
import pytz
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# 📍 Location: Kirkland, WA
CITY_NAME = "Kirkland"
LATITUDE = 47.6858
LONGITUDE = -122.2087 #-122.1917 - align with the Weather Plus Plugin
TIMEZONE = "America/Los_Angeles"

# 🔧 Config
SUN_ANGLE_MIN = 10  # degrees
SUN_ANGLE_MAX = 70  # degrees
AZIMUTH_MIN = 200  # degrees
AZIMUTH_MAX = 310  # degrees
CLOUD_COVER_THRESHOLD = 30  # % cloud cover max

# 🌐 Homebridge webhook
ACCESSORY_ID = "sun-incline"
HOMEbridge_BASE_URL = "http://homebridge.local:51828"
WEBHOOK_ON_URL = f"{HOMEbridge_BASE_URL}/?accessoryId={ACCESSORY_ID}&state=true"
WEBHOOK_OFF_URL = f"{HOMEbridge_BASE_URL}/?accessoryId={ACCESSORY_ID}&state=false"

# 🌤 OpenWeatherMap API
OWM_API_KEY = os.getenv("OWM_API_KEY")

if not OWM_API_KEY:
    raise ValueError("⚠️  OpenWeatherMap API key is missing. Please set it in the .env file.")

# ☁️ Get cloud cover from OpenWeatherMap
def get_cloud_cover():
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LATITUDE}&lon={LONGITUDE}&appid={OWM_API_KEY}&units=metric"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        clouds = data.get("clouds", {}).get("all", 100)
        return clouds
    except Exception as e:
        print(f"⚠️  Failed to get cloud cover: {e}")
        return 100  # Default to "very cloudy" if API fails

def get_cloud_cover3():
    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={LATITUDE}&lon={LONGITUDE}&exclude=minutely,hourly,daily,alerts&appid={OWM_API_KEY}&units=metric"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        clouds = data.get("current", {}).get("clouds", 100)
        return clouds
    except Exception as e:
        print(f"⚠️  Failed to get One Call weather data: {e}")
        return 100


def main():
    # 🌍 Set up location
    city = LocationInfo(CITY_NAME, "USA", TIMEZONE, LATITUDE, LONGITUDE)
    tz = pytz.timezone(city.timezone)
    now = datetime.now(tz)
   
    # 🌅 Calculate solar elevation and azimuth
    el = elevation(city.observer, now)
    az = azimuth(city.observer, now)

    # ☁️ Weather condition
    cloud_cover = get_cloud_cover3()    

    print(f"[{now.strftime('%m-%d-%Y %H:%M:%S %z')}] Solar Elevation: {el:.2f}° Azimuth: {az:.1f}° Cloud Cover: {cloud_cover}%")
   
   
    # 🚀 Trigger Homebridge webhook
    if(
        SUN_ANGLE_MIN <= el <= SUN_ANGLE_MAX and
        AZIMUTH_MIN <= az <= AZIMUTH_MAX and
        cloud_cover <= CLOUD_COVER_THRESHOLD
    ):
        print("✅ Conditions met → triggering sensor ON")
        try:
            requests.get(WEBHOOK_ON_URL, timeout=5)
        except Exception as e:
            print(f"⚠️  Solar Webhook ON failed: {e}")
    else:
        print("🚫 Conditions not met → triggering sensor OFF")
        try:
            requests.get(WEBHOOK_OFF_URL, timeout=5)
        except Exception as e:
            print(f"⚠️  Solar Webhook OFF failed: {e}")

if __name__ == "__main__":
    main()