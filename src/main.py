#!/usr/bin/env python3
from astral import LocationInfo
from astral.sun import elevation, azimuth #, sun
from datetime import datetime
import requests
from math import degrees
import pytz
from dotenv import load_dotenv
import os
import time  # For the loop delay
import argparse

# Load environment variables from .env file
load_dotenv()

# 📍 Location: Kirkland, WA
CITY_NAME = "Kirkland"
LATITUDE = 47.6858
LONGITUDE = -122.2087 #-122.1917 - align with the Weather Plus Plugin
TIMEZONE = "America/Los_Angeles"
COUNTRY_NAME = "USA"

# 🔧 Config
SUN_ANGLE_MIN = 7  # degrees
SUN_ANGLE_MAX = 42  # degrees
AZIMUTH_MIN = 200  # degrees
AZIMUTH_MAX = 310  # degrees
BRITNESS_THRESHOLD = 75  # threshold for brightness score to trigger webhook

# 🌐 Homebridge webhook
ACCESSORY_ID = "sun-incline"
HOMEbridge_BASE_URL = "http://homebridge.local:51828"
WEBHOOK_ON_URL = f"{HOMEbridge_BASE_URL}/?accessoryId={ACCESSORY_ID}&state=true"
WEBHOOK_OFF_URL = f"{HOMEbridge_BASE_URL}/?accessoryId={ACCESSORY_ID}&state=false"

# 🌤 OpenWeatherMap API
OWM_API_KEY = os.getenv("OWM_API_KEY")

if not OWM_API_KEY:
    raise ValueError("⚠️  OpenWeatherMap API key is missing. Please set it in the .env file.")

# --- Function to fetch weather data from OpenWeatherMap API ---
# This function fetches the weather data from OpenWeatherMap API and returns the entire response.
def get_weather_data():
    """
    Fetch weather data from OpenWeatherMap API and return the entire response.
    """
    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={LATITUDE}&lon={LONGITUDE}&exclude=minutely,hourly,daily,alerts&appid={OWM_API_KEY}&units=metric"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        return data  # Return the entire JSON response
    except Exception as e:
        print(f"⚠️  Failed to get weather data: {e}")
        return None  # Return None if the API call fails

# --- Function to compute brightness score based on UVI, clouds, elevation, and azimuth ---
def compute_brightness_score(uvi, clouds, elev, azim):
    # 1. Elevation score: 1 if within glare range
    elev_score = 1.0 if SUN_ANGLE_MIN <= elev <= SUN_ANGLE_MAX else 0.0

    # 2. Azimuth score: 1 if sun is facing the window
    azim_score = 1.0 if AZIMUTH_MIN <= azim <= AZIMUTH_MAX else 0.0

    # 3. Cloud clarity score: 1.0 for clear skies, 0.0 for fully overcast
    cloud_score = max(0, min((100 - clouds) / 100, 1.0))

    # 4. UVI score: placeholder, always 1 for now
    uvi_score = 1.0  # Will evolve based on future empirical insight

    # Final score: Multiplicative model (binary gates + clarity)
    score = max(0, min(elev_score * azim_score * cloud_score * uvi_score * 100, 100))

    # Display table
    print(f"{'Metric':<15}{'Value':<15}{'Score':<15}")
    print(f"{'-' * 45}")
    print(f"{'Elevation':<15}{f'{elev:.2f}°':<15}{f'{elev_score:.2f}':<15}")
    print(f"{'Azimuth':<15}{f'{azim:.2f}°':<15}{f'{azim_score:.2f}':<15}")
    print(f"{'Cloud':<15}{f'{clouds:.1f}%':<15}{f'{cloud_score:.2f}':<15}")
    print(f"{'UVI':<15}{f'{uvi:.1f}':<15}{f'{uvi_score:.2f}':<15}")
    print(f"{'-' * 45}")
    print(f"{'Score (product)':<15}{'':<15}{f'{score:.2f}':<15}")
    
    return score

# ☀️ Function to perform sun observation and trigger webhooks
def sun_observation():
    # 🌍 Set up location
    city = LocationInfo(CITY_NAME, COUNTRY_NAME, TIMEZONE, LATITUDE, LONGITUDE)
    tz = pytz.timezone(city.timezone)
    now = datetime.now(tz)
   
    # 🌅 Calculate solar elevation and azimuth
    el = elevation(city.observer, now)
    az = azimuth(city.observer, now)

    # ☁️ Fetch weather data
    weather_data = get_weather_data()
    if not weather_data:
        print("⚠️  Unable to fetch weather data. Skipping observation.")
        return

    # Extract specific fields from the weather data
    clouds = weather_data.get("current", {}).get("clouds", 100)  # Default to 100% cloud cover
    uvi = weather_data.get("current", {}).get("uvi", 0)  # Default to 0 UV index

    # 🌞 Compute brightness score
    print(f"\033[1;33mWeather observation for {CITY_NAME} at [{now.strftime('%m-%d-%Y %H:%M:%S %z')}]:\033[0m")
    brightness_score = compute_brightness_score(uvi, clouds, el, az)
   
    # 🚀 Trigger Homebridge webhook
    if (brightness_score >= BRITNESS_THRESHOLD):
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
            sun_observation()
            print(f"⏳ Waiting for {args.t} seconds...")
            time.sleep(args.t)
    else:
        # Run once and exit
        sun_observation()

if __name__ == "__main__":
    main()