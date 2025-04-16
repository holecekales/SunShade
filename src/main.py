#!/usr/bin/env python3
from astral import LocationInfo
from astral.sun import elevation, azimuth #, sun
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
    SUN_ANGLE_MIN = 10  # degrees
    SUN_ANGLE_MAX = 70  # degrees
    WEST_MIN = 200  # degrees
    WEST_MAX = 310  # degrees

    # 🌐 Homebridge webhook
    ACCESSORY_ID = "sun-incline"
    HOMEbridge_BASE_URL = "http://homebridge.local:51828"
    WEBHOOK_ON_URL = f"{HOMEbridge_BASE_URL}/?accessoryId={ACCESSORY_ID}&state=true"
    WEBHOOK_OFF_URL = f"{HOMEbridge_BASE_URL}/?accessoryId={ACCESSORY_ID}&state=false"

    # 🌍 Set up location
    city = LocationInfo(CITY_NAME, "USA", TIMEZONE, LATITUDE, LONGITUDE)
    tz = pytz.timezone(city.timezone)
    now = datetime.now(tz)
   
    # 🌅 Calculate solar elevation and azimuth
    el = elevation(city.observer, now)
    az = azimuth(city.observer, now)
    print(f"[{now}] Solar Elevation: {el:.2f}° Azimuth: {az:.1f}°")
   

    # 🚀 Trigger Homebridge webhook
    try:
        if SUN_ANGLE_MIN <= el <= SUN_ANGLE_MAX and WEST_MIN <= az <= WEST_MAX:
            print("→ 🔆 in window — triggering ON (contact)")
            requests.get(WEBHOOK_ON_URL, timeout=5)
        else:
            print("→ 🔆 not in window — triggering OFF (no contact)")
            requests.get(WEBHOOK_OFF_URL, timeout=5)
    except requests.RequestException as e:
        print(f"⚠️ Error triggering webhook: {e}")


if __name__ == "__main__":
    main()