import requests


def fetch_coordinates(apikey, address):
    base_url = 'https://geocode-maps.yandex.ru/1.x'
    response = requests.get(base_url, params={
        'geocode': address,
        'apikey': apikey,
        'format': 'json',
    }, timeout=5)
    response.raise_for_status()

    found_places = (
        response.json()
        .get('response', {})
        .get('GeoObjectCollection', {})
        .get('featureMember')
    )
    if not found_places:
        return None

    most_relevant = found_places[0]
    position = (
        most_relevant
        .get('GeoObject', {})
        .get('Point', {})
        .get('pos')
    )
    if not position:
        return None

    coordinates = position.split()
    if len(coordinates) != 2:
        return None

    lon, lat = coordinates
    return float(lat), float(lon)
