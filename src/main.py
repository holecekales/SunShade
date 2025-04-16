#!/usr/bin/env python3
from astral import LocationInfo
from astral.location import Observer
from astral.sun import elevation
from datetime import datetime
import requests
from math import degrees
import pytz


def main():
    # 📍 Location: Kirkland, WA
    CITY_NAME = "Kirkland"
    LATITUDE = 47.6858
    LONGITUDE = -122.1917
    TIMEZONE = "America/Los_Angeles"

    # 🔧 Config
    SUN_ANGLE_THRESHOLD = 10  # degrees
    ACCESSORY_ID = "sun-incline"
    HOMEbridge_BASE_URL = "http://homebridge.local:51828"
    WEBHOOK_ON_URL = f"{HOMEbridge_BASE_URL}/?accessoryId={ACCESSORY_ID}&state=true"
    WEBHOOK_OFF_URL = f"{HOMEbridge_BASE_URL}/?accessoryId={ACCESSORY_ID}&state=false"


    # 🌍 Set up location
    city = LocationInfo(CITY_NAME, "USA", TIMEZONE, LATITUDE, LONGITUDE)
    tz = pytz.timezone(city.timezone)
    now = datetime.now(tz)
   
    # 🌅 Calculate solar elevation
    sun = elevation(city.observer, now)
    print(f"[{now}] Solar Elevation: {sun:.2f}°")

    # 🚀 Trigger Homebridge webhook
    try:
        if sun < SUN_ANGLE_THRESHOLD:
            print("→ Below threshold — triggering ON (contact)")
            requests.get(WEBHOOK_ON_URL, timeout=5)
        else:
            print("→ Above threshold — triggering OFF (no contact)")
            requests.get(WEBHOOK_OFF_URL, timeout=5)
    except requests.RequestException as e:
        print(f"⚠️ Error triggering webhook: {e}")


if __name__ == "__main__":
    main()