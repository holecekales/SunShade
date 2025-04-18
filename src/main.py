#!/usr/bin/env python3
from astral import LocationInfo
from astral.sun import elevation, azimuth #, sun
from datetime import datetime, timedelta
import requests
from math import degrees
import pytz
from dotenv import load_dotenv
import os
import time  # For the loop delay
import argparse
import logging


# Load environment variables from .env file
load_dotenv()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

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
BRITNESS_CLOSE_THRESHOLD = 33  # threshold for brightness score to trigger webhook

# 🌐 Homebridge webhook
ACCESSORY_ID = "sun-incline"
HOMEBRIDGE_URL = "http://homebridge.local:51828"
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

def log_forecast_table(current, forecast_points, threshold=BRITNESS_CLOSE_THRESHOLD):
    def format_cell(value, unit, indicator=None, width=10):
        """Right-align the value + unit, then append emoji (monospace-safe)."""
        val_str = f"{value:>5.1f}{unit}"
        if indicator:
            # Add indicator emoji to the right of the value
            # Pad the string to the left to make room for the indicator which is 2 characters wide
            return f"{val_str} {indicator}".ljust(width-1)
        return val_str.ljust(width)

    # Calculate indicators for current values
    elev_in = SUN_ANGLE_MIN <= current['elev'] <= SUN_ANGLE_MAX
    azim_in = AZIMUTH_MIN <= current['azim'] <= AZIMUTH_MAX
    cloud_in = current['clouds'] <= threshold

    # Header
    logging.info(f"{'Time':<6} | {'Elev (°)':<10} | {'Azim (°)':<10} | {'Clouds (%)':<10} | {'UVI':<5}")
    logging.info("-" * 52)

    # Current row
    elev_cell = format_cell(current["elev"], "°", "✅" if elev_in else "❌")
    azim_cell = format_cell(current["azim"], "°", "✅" if azim_in else "❌")
    cloud_cell = format_cell(current["clouds"], "%", "✅" if cloud_in else "❌")
    uvi_cell = f"{current['uvi']:<5.1f}"

    logging.info(f"{'Now':<6} | {elev_cell} | {azim_cell} | {cloud_cell} | {uvi_cell}")

    # Forecast rows (no indicators)
    for point in forecast_points:
        t = point["time"].strftime("%H:%M")
        elev = format_cell(point["elev"], "°")
        azim = format_cell(point["azim"], "°")
        cloud = format_cell(point["clouds"], "%")
        uvi = f"{point['uvi']:<5.1f}"
        logging.info(f"{t:<6} | {elev} | {azim} | {cloud} | {uvi}")

    logging.info("-" * 52)



# extract_remaining_glare_forecast function
def extract_remaining_glare_forecast(city, forecast, tz):
    now = datetime.now(tz)
    glare_points = []

    for hour in forecast:
        dt = datetime.fromtimestamp(hour["dt"], tz)
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

    if glare_points:
        start = glare_points[0]["time"].strftime("%H:%M")
        end = glare_points[-1]["time"].strftime("%H:%M")
        logging.info(f"🌅 Today's glare window: {start} → {end}")
        logging.info(f"🕓 Remaining forecast points: {len(remaining)}")
    else:
        logging.info("❌ No glare window found in forecast today.")

    return remaining

# --- should_close_shades function ---
def should_close_shades(current_obs, glare_forecast, threshold=BRITNESS_CLOSE_THRESHOLD):
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
    if current_clouds > threshold:
        return False
    elif avg_clouds > threshold:
        return False
    else:
        return True

def sun_observation():
    city = LocationInfo(CITY_NAME, COUNTRY_NAME, TIMEZONE, LATITUDE, LONGITUDE)
    tz = pytz.timezone(city.timezone)
    now = datetime.now(tz)

    weather_data = get_weather_data()
    if not weather_data:
        return

    forecast = weather_data.get("hourly", [])
    if not forecast:
        return

    current_obs = {
        "time":     now,
        "clouds":   weather_data.get("current", {}).get("clouds", 100),
        "uvi":      weather_data.get("current", {}).get("uvi", 0),
        "elev":     elevation(city.observer, now),
        "azim":     azimuth(city.observer, now)
    }

    glare_forecast = extract_remaining_glare_forecast(city, forecast, tz)
    log_forecast_table(current_obs, glare_forecast)

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
            sun_observation()
            print(f"⏳ Waiting for {args.t} seconds...")
            time.sleep(args.t)
    else:
        # Run once and exit
        sun_observation()

if __name__ == "__main__":
    main()