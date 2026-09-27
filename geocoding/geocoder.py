from datetime import timedelta

import requests

from django.conf import settings
from django.utils import timezone

from geocoding.models import Place


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


def get_coordinates(address):
    place = Place.objects.filter(address=address).first()
    if place and is_fresh(place):
        return coordinates_of(place)

    try:
        coordinates = fetch_coordinates(settings.YANDEX_GEOCODER_API_KEY, address)
    except requests.exceptions.RequestException:
        # Сеть не дошла. Не записываем пустые координаты с свежей датой,
        # иначе повтор заблокируется до истечения срока годности.
        return None

    latitude, longitude = coordinates if coordinates else (None, None)
    Place.objects.update_or_create(
        address=address,
        defaults={
            'latitude': latitude,
            'longitude': longitude,
        },
    )
    return coordinates


def is_fresh(place):
    return timezone.now() - place.queried_at < timedelta(
        seconds=settings.GEOCODER_CACHE_TIMEOUT
    )


def coordinates_of(place):
    if place.latitude is None or place.longitude is None:
        return None
    return place.latitude, place.longitude
