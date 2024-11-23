
import requests

# Replace 'YOUR_API_KEY' with your actual Geolocation API key from GCP
API_KEY = 'AIzaSyAfuGZWe9GhaZW-fguEqzHqKa1SEgVd8Y8'

def get_current_location():
    url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={API_KEY}"
    
    try:
        # Sending a POST request to the API
        response = requests.post(url, json={})
        response.raise_for_status()
        
        # Parsing the response
        location_data = response.json()
        latitude = location_data['location']['lat']
        longitude = location_data['location']['lng']
        
        return latitude, longitude
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching location data: {e}")
        return None, None

# Get the current location
lat, lng = get_current_location()
if lat and lng:
    print(f"Current Location: Latitude = {lat}, Longitude = {lng}")
else:
    print("Unable to fetch location data.")
