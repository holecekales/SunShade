#!/usr/bin/env python3
from astral import LocationInfo
from astral.sun import elevation, azimuth, sun
from datetime import datetime, timedelta
import requests
from math import degrees
import pytz
from dotenv import load_dotenv
import os
import time  # For the loop delay
import argparse
import logging
from logging_utils import log_solar_data


# Load environment variables from .env file
load_dotenv()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# 📍 Location: Kirkland, WA
# Load configuration from environment variables
CITY_NAME = os.getenv("CITY_NAME", "Kirkland")
LATITUDE = float(os.getenv("LATITUDE", 47.6858))
LONGITUDE = float(os.getenv("LONGITUDE", -122.2087))  # -122.1917 - align with the Weather Plus Plugin
TIMEZONE = os.getenv("TIMEZONE", "America/Los_Angeles")
COUNTRY_NAME = os.getenv("COUNTRY_NAME", "USA")

# 🔧 Config
SUN_ANGLE_MIN = float(os.getenv("SUN_ANGLE_MIN", 7))  # degrees
SUN_ANGLE_MAX = float(os.getenv("SUN_ANGLE_MAX", 42))  # degrees
AZIMUTH_MIN = float(os.getenv("AZIMUTH_MIN", 200))  # degrees
AZIMUTH_MAX = float(os.getenv("AZIMUTH_MAX", 310))  # degrees
BRITNESS_CLOSE_THRESHOLD = int(os.getenv("BRITNESS_CLOSE_THRESHOLD", 33))  # threshold for brightness score to trigger webhook

# 🌐 Homebridge webhook
ACCESSORY_ID = os.getenv("ACCESSORY_ID", "sun-incline")
HOMEBRIDGE_HOST = os.getenv("HOMEBRIDGE_HOST", "http://homebridge.local")
HOMEBRIDGE_PORT = os.getenv("HOMEBRIDGE_PORT", "51828")
HOMEBRIDGE_URL = f"{HOMEBRIDGE_HOST}:{HOMEBRIDGE_PORT}"
WEBHOOK_ON_URL = f"{HOMEBRIDGE_URL}/?accessoryId={ACCESSORY_ID}&state=true"
WEBHOOK_OFF_URL = f"{HOMEBRIDGE_URL}/?accessoryId={ACCESSORY_ID}&state=false"

# 🌤 OpenWeatherMap API
OWM_API_KEY = os.getenv("OWM_API_KEY")

if not OWM_API_KEY:
    raise ValueError("⚠️  OpenWeatherMap API key is missing. Please set it in the .env file.")

# --- Function to fetch weather data from OpenWeatherMap API ---
# This function fetches the weather data from OpenWeatherMap API and returns the entire response.
def get_weather_data():
    url = f"https://api.openweathermap.org/data/3.0/onecall"
    
    params = {
        "lat": LATITUDE,
        "lon": LONGITUDE,
        "appid": OWM_API_KEY,
        "units": "metric",  # Use metric units (Celsius)
        "exclude": "minutely,daily,alerts", # Exclude unnecessary data (hourly is included by default)
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        return data  # Return the entire JSON response
    except Exception as e:
        print(f"⚠️  Failed to get weather data: {e}")
        return None  # Return None if the API call fails

# --- Function to calculate glare window for today ---
def calculate_glare_window(observer, tz):
    date_today = datetime.now(tz).date()
    solar_times = sun(observer, date=date_today, tzinfo=tz)
    start = solar_times["sunrise"]
    end = solar_times["sunset"]

    step = timedelta(minutes=1)
    glare_start = None
    glare_end = None

    t = start
    while t <= end:
        elev = elevation(observer, t)
        azim = azimuth(observer, t)

        if SUN_ANGLE_MIN <= elev <= SUN_ANGLE_MAX and AZIMUTH_MIN <= azim <= AZIMUTH_MAX:
            if not glare_start:
                glare_start = t
            glare_end = t  # keep updating as long as it's in range

        t += step

    gw = {
        "start": glare_start,
        "end": glare_end
    }

    return gw

# extract_remaining_glare_forecast function
def get_glare_forecast(city, forecast, tz):
    now = datetime.now(tz)
    end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=tz)  # End of the current day
    glare_points = []

    for hour in forecast:
        dt = datetime.fromtimestamp(hour["dt"], tz)

         # Skip points outside the current day
        if dt > end_of_day:
            break

        elev = elevation(city.observer, dt)
        azim = azimuth(city.observer, dt)

        if SUN_ANGLE_MIN <= elev <= SUN_ANGLE_MAX and AZIMUTH_MIN <= azim <= AZIMUTH_MAX:
            glare_points.append({
                "time": dt,
                "clouds": hour["clouds"],
                "uvi": hour.get("uvi", 0),
                "elev": elev,
                "azim": azim
            })

    remaining = [pt for pt in glare_points if pt["time"] >= now]
    
    return remaining

# --- should_close_shades function ---
def should_close_shades(current_obs, glare_forecast):
    avg_clouds = 0
    if glare_forecast:
        avg_clouds = sum(p["clouds"] for p in glare_forecast) / len(glare_forecast)

    current_clouds = current_obs["clouds"]
    current_elev = current_obs["elev"]
    current_azim = current_obs["azim"]

    # Check if sun is within the glare bounds
    if not (SUN_ANGLE_MIN <= current_elev <= SUN_ANGLE_MAX and AZIMUTH_MIN <= current_azim <= AZIMUTH_MAX):
        return False
    
    # Check cloud conditions
    if current_clouds > BRITNESS_CLOSE_THRESHOLD:
        return False
    elif avg_clouds > BRITNESS_CLOSE_THRESHOLD:
        return False
    else:
        return True

# --- Main function to evaluate sun conditions and trigger webhooks ---
# This function evaluates the current sun conditions and triggers webhooks based on the results.
def sun_evaluation():
    city = LocationInfo(CITY_NAME, COUNTRY_NAME, TIMEZONE, LATITUDE, LONGITUDE)
    tz = pytz.timezone(city.timezone)
    now = datetime.now(tz)

    weather_data = get_weather_data()
    if not weather_data:
        return

    forecast = weather_data.get("hourly", [])
    if not forecast:
        return

    # Calculate current observations adn indicators
    elev = elevation(city.observer, now)
    azim = azimuth(city.observer, now)
    clouds = weather_data.get("current", {}).get("clouds", 100)

    current_obs = {
        "time":     now,
        "clouds":   clouds,
        "uvi":      weather_data.get("current", {}).get("uvi", 0),
        "elev":     elevation(city.observer, now),
        "azim":     azimuth(city.observer, now),
        "elev_in":  SUN_ANGLE_MIN <= elev <= SUN_ANGLE_MAX,
        "azim_in":  AZIMUTH_MIN <= azim <= AZIMUTH_MAX,
        "cloud_in": clouds <= BRITNESS_CLOSE_THRESHOLD
    }

    glare_forecast = get_glare_forecast(city, forecast, tz)
    glare_window = calculate_glare_window(city.observer, tz)

    # Log solar data
    log_solar_data(city, current_obs, glare_forecast, glare_window)

    if should_close_shades(current_obs, glare_forecast):
        try:
            logging.info("🔽 CLOSE SHADES → Triggering webhook ON")
            requests.get(WEBHOOK_ON_URL, timeout=5)
        except Exception as e:
            logging.error(f"⚠️ Webhook ON failed: {e}")
    else:
        try:
            logging.info("🔼 DO NOT CLOSE → Triggering webhook OFF")
            requests.get(WEBHOOK_OFF_URL, timeout=5)
        except Exception as e:
            logging.error(f"⚠️ Webhook OFF failed: {e}")


# Main function to handle the loop or single execution
def main():
    parser = argparse.ArgumentParser(description="Trigger homebridge based on solar elevation and azimuth.")
    parser.add_argument(
        "-t",
        nargs="?",  # Makes the argument optional
        const=1800,  # Default value if --t is provided without an integer
        type=int,  # Ensures the value is an integer if provided
        help="Loop to require weather and solar data. Time is in seconds. If -t is provided without a value, it defaults to 1800 seconds (30 minutes)."
    )
    args = parser.parse_args()

    if args.t is not None:
        # Run in a loop with the specified or default timeout
        while True:
            sun_evaluation()
            print(f"⏳ Waiting for {args.t} seconds...")
            time.sleep(args.t)
    else:
        # Run once and exit
        sun_evaluation()

if __name__ == "__main__":
    main()