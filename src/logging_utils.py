import logging

def format_cell(value, unit, indicator=None, width=10):
    """Right-align the value + unit, then append emoji (monospace-safe)."""
    val_str = f"{value:>5.1f}{unit}"
    if indicator:
        # Add indicator emoji to the right of the value
        # Pad the string to the left to make room for the indicator which is 2 characters wide
        return f"{val_str} {indicator}".ljust(width-1)
    return val_str.ljust(width)

def log_solar_data(city, current, forecast_points, glare_window):
    """Logs solar data, including glare window and forecast points."""
    # Log glare window
    start = glare_window["start"].strftime("%H:%M")
    end = glare_window["end"].strftime("%H:%M")
    logging.info(f"🌞 Today's glare window in {city.name}: {start} → {end}")

    # Log glare hours remaining
    if not forecast_points:
        logging.info("🕓 No glare hours remaining in forecast for today.")
        return

    logging.info(f"🕓 Glare hours remaining: {len(forecast_points)}")

    # Calculate and log average cloud cover
    avg_clouds = sum(p["clouds"] for p in forecast_points) / len(forecast_points)
    logging.info(f"☁  Average cloud cover in forecast: {avg_clouds:.1f}%")

    # Log table header
    logging.info(f"{'Time':<6} | {'Elev (°)':<10} | {'Azim (°)':<10} | {'Clouds (%)':<10} | {'UVI':<5}")
    logging.info("-" * 52)

    # Log current row
    elev_cell = format_cell(current["elev"], "°", "✅" if current["elev_in"] else "❌")
    azim_cell = format_cell(current["azim"], "°", "✅" if current["azim_in"] else "❌")
    cloud_cell = format_cell(current["clouds"], "%", "✅" if current["cloud_in"] else "❌")
    uvi_cell = f"{current['uvi']:<5.1f}"
    logging.info(f"{'Now':<6} | {elev_cell} | {azim_cell} | {cloud_cell} | {uvi_cell}")

    # Log forecast rows
    for point in forecast_points:
        t = point["time"].strftime("%H:%M")
        elev = format_cell(point["elev"], "°")
        azim = format_cell(point["azim"], "°")
        cloud = format_cell(point["clouds"], "%")
        uvi = f"{point['uvi']:<5.1f}"
        logging.info(f"{t:<6} | {elev} | {azim} | {cloud} | {uvi}")

    logging.info("-" * 52)