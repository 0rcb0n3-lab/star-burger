from datetime import timedelta

import requests

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from geocoding.models import Place

_PREFETCH_CHUNK = 500


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


_STALE = object()


def _chunks(items, size):
    items = list(items)
    for start in range(0, len(items), size):
        yield items[start:start + size]


def prefetch_coordinates(addresses):
    if not addresses:
        return {}

    preloaded = {}
    for chunk in _chunks(addresses, _PREFETCH_CHUNK):
        for place in Place.objects.filter(address__in=chunk):
            preloaded[place.address] = (
                coordinates_of(place) if is_fresh(place) else _STALE
            )
    return preloaded


def get_coordinates(address, preloaded=None):
    if preloaded is None:
        place = Place.objects.filter(address=address).first()
        if place and is_fresh(place):
            return coordinates_of(place)
    elif address in preloaded and preloaded[address] is not _STALE:
        return preloaded[address]

    try:
        coordinates = fetch_coordinates(settings.YANDEX_GEOCODER_API_KEY, address)
    except requests.exceptions.RequestException:
        # Сеть не дошла. Не записываем пустые координаты с свежей датой,
        # иначе повтор заблокируется до истечения срока годности.
        return None

    latitude, longitude = coordinates if coordinates else (None, None)
    try:
        with transaction.atomic():
            Place.objects.update_or_create(
                address=address,
                defaults={
                    'latitude': latitude,
                    'longitude': longitude,
                },
            )
    except IntegrityError:
        pass
    return coordinates


def is_fresh(place):
    return timezone.now() - place.queried_at < timedelta(
        seconds=settings.GEOCODER_PLACE_TTL
    )


def coordinates_of(place):
    if place.latitude is None or place.longitude is None:
        return None
    return place.latitude, place.longitude
