from django.db import models


class Place(models.Model):
    address = models.CharField(
        'адрес',
        max_length=200,
        unique=True,
    )
    latitude = models.FloatField(
        'широта',
        null=True,
        blank=True,
    )
    longitude = models.FloatField(
        'долгота',
        null=True,
        blank=True,
    )
    queried_at = models.DateTimeField(
        'дата запроса',
        auto_now=True,
    )

    class Meta:
        verbose_name = 'место'
        verbose_name_plural = 'места'

    def __str__(self):
        return self.address
