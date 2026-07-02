"""
Top 100 US cities by population.
Used for randomized test selection — prevents hardcoding for any single city.

Each entry has:
  - city: Display name
  - state: Two-letter state code
  - osmnx_query: String for osmnx.graph_from_place()
  - lat/lon: Approximate city center (for bounding box construction)
"""

TOP_100_US_CITIES = [
    {"rank": 1, "city": "New York City", "state": "NY", "osmnx_query": "New York, New York, USA", "lat": 40.7128, "lon": -74.0060},
    {"rank": 2, "city": "Los Angeles", "state": "CA", "osmnx_query": "Los Angeles, California, USA", "lat": 34.0522, "lon": -118.2437},
    {"rank": 3, "city": "Chicago", "state": "IL", "osmnx_query": "Chicago, Illinois, USA", "lat": 41.8781, "lon": -87.6298},
    {"rank": 4, "city": "Houston", "state": "TX", "osmnx_query": "Houston, Texas, USA", "lat": 29.7604, "lon": -95.3698},
    {"rank": 5, "city": "Phoenix", "state": "AZ", "osmnx_query": "Phoenix, Arizona, USA", "lat": 33.4484, "lon": -112.0740},
    {"rank": 6, "city": "Philadelphia", "state": "PA", "osmnx_query": "Philadelphia, Pennsylvania, USA", "lat": 39.9526, "lon": -75.1652},
    {"rank": 7, "city": "San Antonio", "state": "TX", "osmnx_query": "San Antonio, Texas, USA", "lat": 29.4241, "lon": -98.4936},
    {"rank": 8, "city": "San Diego", "state": "CA", "osmnx_query": "San Diego, California, USA", "lat": 32.7157, "lon": -117.1611},
    {"rank": 9, "city": "Dallas", "state": "TX", "osmnx_query": "Dallas, Texas, USA", "lat": 32.7767, "lon": -96.7970},
    {"rank": 10, "city": "Jacksonville", "state": "FL", "osmnx_query": "Jacksonville, Florida, USA", "lat": 30.3322, "lon": -81.6557},
    {"rank": 11, "city": "Austin", "state": "TX", "osmnx_query": "Austin, Texas, USA", "lat": 30.2672, "lon": -97.7431},
    {"rank": 12, "city": "Fort Worth", "state": "TX", "osmnx_query": "Fort Worth, Texas, USA", "lat": 32.7555, "lon": -97.3308},
    {"rank": 13, "city": "San Jose", "state": "CA", "osmnx_query": "San Jose, California, USA", "lat": 37.3382, "lon": -121.8863},
    {"rank": 14, "city": "Columbus", "state": "OH", "osmnx_query": "Columbus, Ohio, USA", "lat": 39.9612, "lon": -82.9988},
    {"rank": 15, "city": "Charlotte", "state": "NC", "osmnx_query": "Charlotte, North Carolina, USA", "lat": 35.2271, "lon": -80.8431},
    {"rank": 16, "city": "Indianapolis", "state": "IN", "osmnx_query": "Indianapolis, Indiana, USA", "lat": 39.7684, "lon": -86.1581},
    {"rank": 17, "city": "San Francisco", "state": "CA", "osmnx_query": "San Francisco, California, USA", "lat": 37.7749, "lon": -122.4194},
    {"rank": 18, "city": "Seattle", "state": "WA", "osmnx_query": "Seattle, Washington, USA", "lat": 47.6062, "lon": -122.3321},
    {"rank": 19, "city": "Denver", "state": "CO", "osmnx_query": "Denver, Colorado, USA", "lat": 39.7392, "lon": -104.9903},
    {"rank": 20, "city": "Washington", "state": "DC", "osmnx_query": "Washington, District of Columbia, USA", "lat": 38.9072, "lon": -77.0369},
    {"rank": 21, "city": "Nashville", "state": "TN", "osmnx_query": "Nashville, Tennessee, USA", "lat": 36.1627, "lon": -86.7816},
    {"rank": 22, "city": "Oklahoma City", "state": "OK", "osmnx_query": "Oklahoma City, Oklahoma, USA", "lat": 35.4676, "lon": -97.5164},
    {"rank": 23, "city": "El Paso", "state": "TX", "osmnx_query": "El Paso, Texas, USA", "lat": 31.7619, "lon": -106.4850},
    {"rank": 24, "city": "Boston", "state": "MA", "osmnx_query": "Boston, Massachusetts, USA", "lat": 42.3601, "lon": -71.0589},
    {"rank": 25, "city": "Portland", "state": "OR", "osmnx_query": "Portland, Oregon, USA", "lat": 45.5152, "lon": -122.6784},
    {"rank": 26, "city": "Las Vegas", "state": "NV", "osmnx_query": "Las Vegas, Nevada, USA", "lat": 36.1699, "lon": -115.1398},
    {"rank": 27, "city": "Memphis", "state": "TN", "osmnx_query": "Memphis, Tennessee, USA", "lat": 35.1495, "lon": -90.0490},
    {"rank": 28, "city": "Louisville", "state": "KY", "osmnx_query": "Louisville, Kentucky, USA", "lat": 38.2527, "lon": -85.7585},
    {"rank": 29, "city": "Baltimore", "state": "MD", "osmnx_query": "Baltimore, Maryland, USA", "lat": 39.2904, "lon": -76.6122},
    {"rank": 30, "city": "Milwaukee", "state": "WI", "osmnx_query": "Milwaukee, Wisconsin, USA", "lat": 43.0389, "lon": -87.9065},
    {"rank": 31, "city": "Albuquerque", "state": "NM", "osmnx_query": "Albuquerque, New Mexico, USA", "lat": 35.0844, "lon": -106.6504},
    {"rank": 32, "city": "Tucson", "state": "AZ", "osmnx_query": "Tucson, Arizona, USA", "lat": 32.2226, "lon": -110.9747},
    {"rank": 33, "city": "Fresno", "state": "CA", "osmnx_query": "Fresno, California, USA", "lat": 36.7378, "lon": -119.7871},
    {"rank": 34, "city": "Sacramento", "state": "CA", "osmnx_query": "Sacramento, California, USA", "lat": 38.5816, "lon": -121.4944},
    {"rank": 35, "city": "Mesa", "state": "AZ", "osmnx_query": "Mesa, Arizona, USA", "lat": 33.4152, "lon": -111.8315},
    {"rank": 36, "city": "Kansas City", "state": "MO", "osmnx_query": "Kansas City, Missouri, USA", "lat": 39.0997, "lon": -94.5786},
    {"rank": 37, "city": "Atlanta", "state": "GA", "osmnx_query": "Atlanta, Georgia, USA", "lat": 33.7490, "lon": -84.3880},
    {"rank": 38, "city": "Omaha", "state": "NE", "osmnx_query": "Omaha, Nebraska, USA", "lat": 41.2565, "lon": -95.9345},
    {"rank": 39, "city": "Colorado Springs", "state": "CO", "osmnx_query": "Colorado Springs, Colorado, USA", "lat": 38.8339, "lon": -104.8214},
    {"rank": 40, "city": "Raleigh", "state": "NC", "osmnx_query": "Raleigh, North Carolina, USA", "lat": 35.7796, "lon": -78.6382},
    {"rank": 41, "city": "Long Beach", "state": "CA", "osmnx_query": "Long Beach, California, USA", "lat": 33.7701, "lon": -118.1937},
    {"rank": 42, "city": "Virginia Beach", "state": "VA", "osmnx_query": "Virginia Beach, Virginia, USA", "lat": 36.8529, "lon": -75.9780},
    {"rank": 43, "city": "Miami", "state": "FL", "osmnx_query": "Miami, Florida, USA", "lat": 25.7617, "lon": -80.1918},
    {"rank": 44, "city": "Oakland", "state": "CA", "osmnx_query": "Oakland, California, USA", "lat": 37.8044, "lon": -122.2712},
    {"rank": 45, "city": "Minneapolis", "state": "MN", "osmnx_query": "Minneapolis, Minnesota, USA", "lat": 44.9778, "lon": -93.2650},
    {"rank": 46, "city": "Tulsa", "state": "OK", "osmnx_query": "Tulsa, Oklahoma, USA", "lat": 36.1540, "lon": -95.9928},
    {"rank": 47, "city": "Tampa", "state": "FL", "osmnx_query": "Tampa, Florida, USA", "lat": 27.9506, "lon": -82.4572},
    {"rank": 48, "city": "Arlington", "state": "TX", "osmnx_query": "Arlington, Texas, USA", "lat": 32.7357, "lon": -97.1081},
    {"rank": 49, "city": "New Orleans", "state": "LA", "osmnx_query": "New Orleans, Louisiana, USA", "lat": 29.9511, "lon": -90.0715},
    {"rank": 50, "city": "Wichita", "state": "KS", "osmnx_query": "Wichita, Kansas, USA", "lat": 37.6872, "lon": -97.3301},
    {"rank": 51, "city": "Bakersfield", "state": "CA", "osmnx_query": "Bakersfield, California, USA", "lat": 35.3733, "lon": -119.0187},
    {"rank": 52, "city": "Cleveland", "state": "OH", "osmnx_query": "Cleveland, Ohio, USA", "lat": 41.4993, "lon": -81.6944},
    {"rank": 53, "city": "Aurora", "state": "CO", "osmnx_query": "Aurora, Colorado, USA", "lat": 39.7294, "lon": -104.8319},
    {"rank": 54, "city": "Anaheim", "state": "CA", "osmnx_query": "Anaheim, California, USA", "lat": 33.8366, "lon": -117.9143},
    {"rank": 55, "city": "Honolulu", "state": "HI", "osmnx_query": "Honolulu, Hawaii, USA", "lat": 21.3069, "lon": -157.8583},
    {"rank": 56, "city": "Santa Ana", "state": "CA", "osmnx_query": "Santa Ana, California, USA", "lat": 33.7455, "lon": -117.8677},
    {"rank": 57, "city": "Riverside", "state": "CA", "osmnx_query": "Riverside, California, USA", "lat": 33.9533, "lon": -117.3962},
    {"rank": 58, "city": "Corpus Christi", "state": "TX", "osmnx_query": "Corpus Christi, Texas, USA", "lat": 27.8006, "lon": -97.3964},
    {"rank": 59, "city": "Lexington", "state": "KY", "osmnx_query": "Lexington, Kentucky, USA", "lat": 38.0406, "lon": -84.5037},
    {"rank": 60, "city": "Henderson", "state": "NV", "osmnx_query": "Henderson, Nevada, USA", "lat": 36.0395, "lon": -114.9817},
    {"rank": 61, "city": "Stockton", "state": "CA", "osmnx_query": "Stockton, California, USA", "lat": 37.9577, "lon": -121.2908},
    {"rank": 62, "city": "Saint Paul", "state": "MN", "osmnx_query": "Saint Paul, Minnesota, USA", "lat": 44.9537, "lon": -93.0900},
    {"rank": 63, "city": "Cincinnati", "state": "OH", "osmnx_query": "Cincinnati, Ohio, USA", "lat": 39.1031, "lon": -84.5120},
    {"rank": 64, "city": "St. Louis", "state": "MO", "osmnx_query": "St. Louis, Missouri, USA", "lat": 38.6270, "lon": -90.1994},
    {"rank": 65, "city": "Pittsburgh", "state": "PA", "osmnx_query": "Pittsburgh, Pennsylvania, USA", "lat": 40.4406, "lon": -79.9959},
    {"rank": 66, "city": "Greensboro", "state": "NC", "osmnx_query": "Greensboro, North Carolina, USA", "lat": 36.0726, "lon": -79.7920},
    {"rank": 67, "city": "Lincoln", "state": "NE", "osmnx_query": "Lincoln, Nebraska, USA", "lat": 40.8136, "lon": -96.7026},
    {"rank": 68, "city": "Orlando", "state": "FL", "osmnx_query": "Orlando, Florida, USA", "lat": 28.5383, "lon": -81.3792},
    {"rank": 69, "city": "Irvine", "state": "CA", "osmnx_query": "Irvine, California, USA", "lat": 33.6846, "lon": -117.8265},
    {"rank": 70, "city": "Newark", "state": "NJ", "osmnx_query": "Newark, New Jersey, USA", "lat": 40.7357, "lon": -74.1724},
    {"rank": 71, "city": "Durham", "state": "NC", "osmnx_query": "Durham, North Carolina, USA", "lat": 35.9940, "lon": -78.8986},
    {"rank": 72, "city": "Chula Vista", "state": "CA", "osmnx_query": "Chula Vista, California, USA", "lat": 32.6401, "lon": -117.0842},
    {"rank": 73, "city": "Toledo", "state": "OH", "osmnx_query": "Toledo, Ohio, USA", "lat": 41.6528, "lon": -83.5379},
    {"rank": 74, "city": "Fort Wayne", "state": "IN", "osmnx_query": "Fort Wayne, Indiana, USA", "lat": 41.0793, "lon": -85.1394},
    {"rank": 75, "city": "St. Petersburg", "state": "FL", "osmnx_query": "St. Petersburg, Florida, USA", "lat": 27.7676, "lon": -82.6403},
    {"rank": 76, "city": "Laredo", "state": "TX", "osmnx_query": "Laredo, Texas, USA", "lat": 27.5036, "lon": -99.5076},
    {"rank": 77, "city": "Jersey City", "state": "NJ", "osmnx_query": "Jersey City, New Jersey, USA", "lat": 40.7178, "lon": -74.0431},
    {"rank": 78, "city": "Chandler", "state": "AZ", "osmnx_query": "Chandler, Arizona, USA", "lat": 33.3062, "lon": -111.8413},
    {"rank": 79, "city": "Madison", "state": "WI", "osmnx_query": "Madison, Wisconsin, USA", "lat": 43.0731, "lon": -89.4012},
    {"rank": 80, "city": "Lubbock", "state": "TX", "osmnx_query": "Lubbock, Texas, USA", "lat": 33.5779, "lon": -101.8552},
    {"rank": 81, "city": "Scottsdale", "state": "AZ", "osmnx_query": "Scottsdale, Arizona, USA", "lat": 33.4942, "lon": -111.9261},
    {"rank": 82, "city": "Reno", "state": "NV", "osmnx_query": "Reno, Nevada, USA", "lat": 39.5296, "lon": -119.8138},
    {"rank": 83, "city": "Buffalo", "state": "NY", "osmnx_query": "Buffalo, New York, USA", "lat": 42.8864, "lon": -78.8784},
    {"rank": 84, "city": "Gilbert", "state": "AZ", "osmnx_query": "Gilbert, Arizona, USA", "lat": 33.3528, "lon": -111.7890},
    {"rank": 85, "city": "Glendale", "state": "AZ", "osmnx_query": "Glendale, Arizona, USA", "lat": 33.5387, "lon": -112.1860},
    {"rank": 86, "city": "North Las Vegas", "state": "NV", "osmnx_query": "North Las Vegas, Nevada, USA", "lat": 36.1989, "lon": -115.1175},
    {"rank": 87, "city": "Winston-Salem", "state": "NC", "osmnx_query": "Winston-Salem, North Carolina, USA", "lat": 36.0999, "lon": -80.2442},
    {"rank": 88, "city": "Norfolk", "state": "VA", "osmnx_query": "Norfolk, Virginia, USA", "lat": 36.8508, "lon": -76.2859},
    {"rank": 89, "city": "Irving", "state": "TX", "osmnx_query": "Irving, Texas, USA", "lat": 32.8140, "lon": -96.9489},
    {"rank": 90, "city": "Chesapeake", "state": "VA", "osmnx_query": "Chesapeake, Virginia, USA", "lat": 36.7682, "lon": -76.2875},
    {"rank": 91, "city": "Fremont", "state": "CA", "osmnx_query": "Fremont, California, USA", "lat": 37.5485, "lon": -121.9886},
    {"rank": 92, "city": "Garland", "state": "TX", "osmnx_query": "Garland, Texas, USA", "lat": 32.9126, "lon": -96.6389},
    {"rank": 93, "city": "Richmond", "state": "VA", "osmnx_query": "Richmond, Virginia, USA", "lat": 37.5407, "lon": -77.4360},
    {"rank": 94, "city": "Boise", "state": "ID", "osmnx_query": "Boise, Idaho, USA", "lat": 43.6150, "lon": -116.2023},
    {"rank": 95, "city": "San Bernardino", "state": "CA", "osmnx_query": "San Bernardino, California, USA", "lat": 34.1083, "lon": -117.2898},
    {"rank": 96, "city": "Spokane", "state": "WA", "osmnx_query": "Spokane, Washington, USA", "lat": 47.6588, "lon": -117.4260},
    {"rank": 97, "city": "Des Moines", "state": "IA", "osmnx_query": "Des Moines, Iowa, USA", "lat": 41.5868, "lon": -93.6250},
    {"rank": 98, "city": "Birmingham", "state": "AL", "osmnx_query": "Birmingham, Alabama, USA", "lat": 33.5207, "lon": -86.8025},
    {"rank": 99, "city": "Tacoma", "state": "WA", "osmnx_query": "Tacoma, Washington, USA", "lat": 47.2529, "lon": -122.4443},
    {"rank": 100, "city": "Gainesville", "state": "FL", "osmnx_query": "Gainesville, Florida, USA", "lat": 29.6516, "lon": -82.3248},
]


def get_random_cities(n=3, seed=None):
    """Return n randomly selected cities. Uses a seed for reproducibility when needed."""
    import random
    rng = random.Random(seed)
    return rng.sample(TOP_100_US_CITIES, n)


def get_bbox_around_point(lat, lon, radius_km=1.0):
    """
    Return a bounding box (min_lon, min_lat, max_lon, max_lat) centered on
    the given point with the given radius in km. Uses rough degree approximation.
    """
    # ~111km per degree latitude, ~111*cos(lat) per degree longitude
    import math
    lat_offset = radius_km / 111.0
    lon_offset = radius_km / (111.0 * math.cos(math.radians(lat)))
    return (lon - lon_offset, lat - lat_offset, lon + lon_offset, lat + lat_offset)
