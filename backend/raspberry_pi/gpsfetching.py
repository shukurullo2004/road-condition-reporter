import ssl
import certifi
from geopy.geocoders import Nominatim
from datetime import datetime
import time

def getlivegpslocation():
    # Use certifi to update SSL context
    geolocator = Nominatim(user_agent="gps_live_tracker", ssl_context=ssl.create_default_context(cafile=certifi.where()))
    while True:
        try:
            location = geolocator.geocode("New York, USA")

            if location:
                latitude = location.latitude
                longitude = location.longitude
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"Latitude: {latitude}, Longitude: {longitude}, Timestamp: {timestamp}")
            else:
                print("Could not fetch GPS data.")

            time.sleep(5)
        except Exception as e:
            print(f"An error occurred: {e}")
            break

getlivegpslocation()