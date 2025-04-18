# SunShade

SunShade is a Python script that triggers webhook on [Homebridge](https://homebridge.io).The script evaluates position of the sun, cloud cover, and other environmental factors to decide if the webhook should be triggered. The idea is to reduce sun glare in a house. 
It uses OpenWeatherMap API to get weather forecast, and Homebridge Webhooks ([Homebridge Webhooks](https://github.com/benzman81/homebridge-http-webhooks?tab=readme-ov-file#homebridge-http-webhooks)) to trigger contact switch,which than can be used to automate various Apple Homekit appliences. My intent is to automate window shades.

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd SunShade
```

### 2. Set Up Environment Variables
1. **Rename the `.env.example` File**:
   - Locate the `.env.example` file in the project directory.
   - Rename it to `.env`.

   #### On Windows:
   - In File Explorer:
     - Right-click the file and select "Rename."
     - Change the name to `.env`.
   - Or, use the command line:
     ```bash
     ren .env.example .env
     ```

   #### On Mac and Linux:
   - Use the `mv` command in the terminal:
     ```bash
     mv .env.example .env
     ```

2. **Edit the `.env` File**:
   - Open the `.env` file in your text editor.
   - Replace the placeholder values with the actual values for your environment.

   Example `.env` file:
   ```properties
   # OpenWeatherMap API Key
   OWM_API_KEY=your_actual_openweathermap_api_key

   # Location Configuration
   CITY_NAME=Kirkland
   LATITUDE=47.6858
   LONGITUDE=-122.2087
   TIMEZONE=America/Los_Angeles
   COUNTRY_NAME=USA

   # Sun Angle and Azimuth Configuration
   SUN_ANGLE_MIN=7
   SUN_ANGLE_MAX=42
   AZIMUTH_MIN=200
   AZIMUTH_MAX=310
   BRITNESS_CLOSE_THRESHOLD=33

   # Homebridge Webhook Configuration
   ACCESSORY_ID=sun-incline
   HOMEBRIDGE_HOST=http://homebridge.local
   HOMEBRIDGE_PORT=51828
   ```

   - **`OWM_API_KEY`**: Replace `your_actual_openweathermap_api_key` with your OpenWeatherMap API key. You can obtain this by signing up at [OpenWeatherMap](https://openweathermap.org/).
   - **`CITY_NAME`, `LATITUDE`, `LONGITUDE`**: Set these to your location's name and GPS coordinates. Use Google Maps to find your latitude and longitude.
   - **`TIMEZONE`**: Use the IANA timezone for your location (e.g., `America/Los_Angeles` for Pacific Time).
   - **`SUN_ANGLE_MIN`, `SUN_ANGLE_MAX`, `AZIMUTH_MIN`, `AZIMUTH_MAX`**: These define the sun's elevation and azimuth angles for glare calculations. Adjust if needed.
   - **`BRITNESS_CLOSE_THRESHOLD`**: The cloud cover percentage threshold (0-100) above which glare is considered not an issue - so don't close the shutters.
   - **`ACCESSORY_ID`, `HOMEBRIDGE_HOST`, `HOMEBRIDGE_PORT`**: Configure these for your Homebridge setup.

### 3. You can Use the Makefile to Simplify Setup
The project includes a `Makefile` to help automate common tasks. Use the following commands:

- **Install Dependencies**:
  ```bash
  make install
  ```
  This will install all required Python packages from `requirements.txt`.

- **Run the Application**:
  ```bash
  make run
  ```
  This will execute the main script (`src/main.py`).

- **Clean Up**:
  ```bash
  make clean
  ```
  This will remove temporary files, caches, and other unnecessary artifacts.

### 4. (Optional) Create a Virtual Environment
If you prefer to manage dependencies in a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

## Running the Project

To run the application, execute the following command:
```bash
make run
```

## Configuration

The application uses environment variables for configuration. Below is a summary of the key variables:

### OpenWeatherMap API Key
- **`OWM_API_KEY`**: Your API key for accessing the OpenWeatherMap API.

### Location Configuration
- **`CITY_NAME`**: The name of your city (e.g., "Kirkland").
- **`LATITUDE`**: The latitude of your location in decimal degrees.
- **`LONGITUDE`**: The longitude of your location in decimal degrees.
- **`TIMEZONE`**: The IANA timezone of your location (e.g., `America/Los_Angeles`).
- **`COUNTRY_NAME`**: The name of your country (e.g., "USA").

### Sun Angle and Azimuth Configuration
- **`SUN_ANGLE_MIN`**: Minimum sun elevation angle (in degrees) for glare calculations.
- **`SUN_ANGLE_MAX`**: Maximum sun elevation angle (in degrees) for glare calculations.
- **`AZIMUTH_MIN`**: Minimum sun azimuth angle (in degrees) for glare calculations.
- **`AZIMUTH_MAX`**: Maximum sun azimuth angle (in degrees) for glare calculations.
- **`BRITNESS_CLOSE_THRESHOLD`**: Cloud cover percentage threshold (0-100) above which glare is considered blocked.

### Homebridge Webhook Configuration
- **`ACCESSORY_ID`**: Unique accessory ID for the Homebridge webhook.
- **`HOMEBRIDGE_HOST`**: Base URL of your Homebridge server.
- **`HOMEBRIDGE_PORT`**: Port number of your Homebridge server.

## Example Usage

1. **Log Solar Data**:
   - The application logs the glare window, remaining glare hours, and forecast data in a tabular format.

2. **Trigger Webhooks**:
   - Automatically triggers Homebridge webhooks to close or open shades based on glare conditions.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests for any improvements or features you would like to add.

## License

This project is licensed under the MIT License.

## Resources

- [OpenWeatherMap API](https://openweathermap.org/)
- [IANA Time Zone Database](https://www.iana.org/time-zones)
- [Homebridge](https://homebridge.io/)