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
BRITNESS_CLOSE_THRESHOLD = 80  # threshold for brightness score to trigger webhook
BRITNESS_OPEN_THRESHOLD  = 60  # threshold for brightness score to trigger webhook

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
    """
    Fetch weather data from OpenWeatherMap API and return the entire response.
    """
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

# --- Function to perform linear interpolation ---
def lerp(x1, x2, y1, y2, x):
    if x2 == x1:  # Avoid division by zero
        return y1
    return y1 + (y2 - y1) * ((x - x1) / (x2 - x1))

# --- Function to interpolate forecast data ---
def interpolate_forecast(forecast, timezone, interval_minutes=15, duration_minutes=60):
    steps = duration_minutes // interval_minutes
    times = [datetime.fromtimestamp(hour["dt"], timezone) for hour in forecast]
    clouds = [hour["clouds"] for hour in forecast]
    uvi = [hour["uvi"] for hour in forecast]

    # Generate timestamps for interpolation
    start_time = times[0]
    end_time = start_time + timedelta(minutes=duration_minutes)
    interpolated_times = [start_time + timedelta(minutes=i * interval_minutes) for i in range(steps + 1)]

    # Interpolate clouds and UVI manually using lerp
    interpolated_clouds = []
    interpolated_uvi = []

    for t in interpolated_times:
        # Find the two closest forecast points for interpolation
        for i in range(len(times) - 1):
            if times[i] <= t <= times[i + 1]:
                interpolated_clouds.append(lerp(times[i].timestamp(), times[i + 1].timestamp(), clouds[i], clouds[i + 1], t.timestamp()))
                interpolated_uvi.append(lerp(times[i].timestamp(), times[i + 1].timestamp(), uvi[i], uvi[i + 1], t.timestamp()))
                break

    return interpolated_times, interpolated_clouds, interpolated_uvi

# --- Function to calculate solar position ---
def calculate_solar_positions(location, times):
    solar_positions = []
    for time in times:
        el = elevation(location.observer, time)
        az = azimuth(location.observer, time)
        solar_positions.append((el, az))
    return solar_positions

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

# --- Function to decide whether to delay shade movement ---
def should_delay_change(score_now, forecast_scores, direction, threshold_close=0.75, threshold_open=0.5):
    """
    Decide whether to delay shade movement based on forecast scores.
    """
    if direction == "close":
        # If it's bright now but forecast says it will dim soon, delay closing
        if score_now >= threshold_close and any(score < threshold_close for score in forecast_scores):
            return True
    elif direction == "open":
        # If it's dim now but forecast says it will brighten briefly, delay opening
        if score_now <= threshold_open and any(score > threshold_open for score in forecast_scores):
            return True
    return False

# --- Updated sun observation function ---
def sun_observation():
    # 🌍 Set up location
    city = LocationInfo(CITY_NAME, COUNTRY_NAME, TIMEZONE, LATITUDE, LONGITUDE)
    tz = pytz.timezone(city.timezone)
    now = datetime.now(tz)

    # ☁️ Fetch weather data
    weather_data = get_weather_data()
    if not weather_data:
        print("⚠️  Unable to fetch weather data. Skipping observation.")
        return

    # Extract forecast data
    forecast = weather_data.get("hourly", [])
    if not forecast:
        print("⚠️  No forecast data available. Skipping observation.")
        return

    # Interpolate forecast data
    interpolated_times, interpolated_clouds, interpolated_uvi = interpolate_forecast(forecast, tz)

    # Calculate solar positions for interpolated times
    solar_positions = calculate_solar_positions(city, interpolated_times)

    # Compute brightness scores for each interpolated time
    forecast_scores = []
    for i, (time, clouds, uvi) in enumerate(zip(interpolated_times, interpolated_clouds, interpolated_uvi)):
        el, az = solar_positions[i]
        score = compute_brightness_score(uvi, clouds, el, az)
        forecast_scores.append(score)


    # 🌅 Calculate current solar elevation and azimuth
    el = elevation(city.observer, now)
    az = azimuth(city.observer, now)

    # 🌞 Compute current brightness score
    clouds_now = weather_data.get("current", {}).get("clouds", 100)
    uvi_now = weather_data.get("current", {}).get("uvi", 0)
    score_now = compute_brightness_score(uvi_now, clouds_now, el, az)


    # 🚀 Decide whether to delay shade movement
    if score_now >= BRITNESS_CLOSE_THRESHOLD:
        # if should_delay_change(score_now, forecast_scores, direction="close"):
        #     print("⏳ Delaying shade closing based on forecast.")
        #     return
        print("✅ Conditions met → triggering sensor ON")
        try:
            requests.get(WEBHOOK_ON_URL, timeout=5)
        except Exception as e:
            print(f"⚠️  Solar Webhook ON failed: {e}")
    elif score_now <= BRITNESS_CLOSE_THRESHOLD:
        # if should_delay_change(score_now, forecast_scores, direction="open"):
        #     print("⏳ Delaying shade opening based on forecast.")
        #     return
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