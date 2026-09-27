from django.contrib import admin

from .models import Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = [
        'address',
        'latitude',
        'longitude',
        'queried_at',
    ]
    readonly_fields = [
        'queried_at',
    ]
    search_fields = [
        'address',
    ]
