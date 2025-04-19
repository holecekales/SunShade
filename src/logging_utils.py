import logging

# This function formats a cell for logging, right-aligning the value and unit, and optionally adding an indicator.
def format_cell(value, indicator=None, width=10):
    """Right-align the value + unit, then append indicator (monospace-safe)."""
    val_str = f"{value:>5.1f}"
    if indicator:
        # Add indicator to the right of the value
        # Pad the string to the left to make room for the indicator
        return f"{val_str} {indicator}".ljust(width)
    return val_str.ljust(width)

# This function logs solar data, including glare window and forecast points.
def log_solar_data(city, current, forecast_points, glare_window):
    """Logs solar data, including glare window and forecast points."""
    # Log glare window
    start = glare_window["start"].strftime("%H:%M")
    end = glare_window["end"].strftime("%H:%M")
    logging.info(f"Today's glare window in {city.name}: {start} -> {end}")

    avg_clouds = 0
    
    # Log glare hours remaining
    if forecast_points:
        # Calculate and log average cloud cover
        avg_clouds = sum(p["clouds"] for p in forecast_points) / len(forecast_points)
        logging.info(f"Average cloud cover in glare window: {avg_clouds:.1f}%")

    logging.info(f"Glare hours remaining: {len(forecast_points)}")

    # Log table header
    logging.info(f"{'Time':<6} | {'Elev (Deg)':<10} | {'Azim (Deg)':<10} | {'Clouds (%)':<10} | {'UVI':<5}")
    logging.info("-" * 51)

    # Log current row
    elev_cell = format_cell(current["elev"], "[OK]" if current["elev_in"] else "[NO]")
    azim_cell = format_cell(current["azim"], "[OK]" if current["azim_in"] else "[NO]")
    cloud_cell = format_cell(current["clouds"], "[OK]" if current["cloud_in"] else "[NO]")
    uvi_cell = f"{current['uvi']:<5.1f}"
    logging.info(f"{'Now':<6} | {elev_cell} | {azim_cell} | {cloud_cell} | {uvi_cell}")

    # Log forecast rows
    for point in forecast_points:
        t = point["time"].strftime("%H:%M")
        elev = format_cell(point["elev"])
        azim = format_cell(point["azim"])
        cloud = format_cell(point["clouds"])
        uvi = f"{point['uvi']:<5.1f}"
        logging.info(f"{t:<6} | {elev} | {azim} | {cloud} | {uvi}")

    logging.info("-" * 51)