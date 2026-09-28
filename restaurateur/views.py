from collections import defaultdict

from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from geopy import distance

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.db.models import Case, When, Value, IntegerField


from foodcartapp.models import Product, Restaurant, Order, RestaurantMenuItem
from geocoding.geocoder import get_coordinates, prefetch_coordinates


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {item.restaurant_id: item.availability for item in product.menu_items.all()}
        ordered_availability = [availability.get(restaurant.id, False) for restaurant in restaurants]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )

    return render(request, template_name="products_list.html", context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    status_order = Case(
        *[
            When(status=status, then=Value(index))
            for index, (status, _label) in enumerate(Order.STATUS_CHOICES)
        ],
        output_field=IntegerField(),
    )

    orders = (
        Order.objects
        .exclude(status=Order.STATUS_COMPLETED)
        .with_total_price()
        .select_related('restaurant')
        .prefetch_related('items__product')
        .annotate(status_order=status_order)
        .order_by('status_order')
    )

    menu_items = (
        RestaurantMenuItem.objects
        .filter(availability=True)
        .select_related('restaurant', 'product')
    )
    restaurants_by_product = defaultdict(set)
    for menu_item in menu_items:
        restaurants_by_product[menu_item.product_id].add(menu_item.restaurant)

    order_items = list(orders)

    pending = []
    addresses = set()
    for order in order_items:
        if order.restaurant_id:
            continue

        product_ids = {item.product_id for item in order.items.all()}
        restaurant_sets = [restaurants_by_product.get(product_id, set()) for product_id in product_ids]
        available_restaurants = set.intersection(*restaurant_sets) if restaurant_sets else set()
        available_restaurants = {
            restaurant for restaurant in available_restaurants
            if restaurant.address.strip()
        }

        pending.append((order, available_restaurants))
        addresses.add(order.address)
        addresses.update(restaurant.address for restaurant in available_restaurants)

    preloaded = prefetch_coordinates(addresses)

    for order, available_restaurants in pending:
        order_coordinates = get_coordinates(order.address, preloaded)
        order.address_not_found = order_coordinates is None

        restaurants_with_distance = []
        for restaurant in available_restaurants:
            restaurant_coordinates = get_coordinates(restaurant.address, preloaded)
            if order_coordinates and restaurant_coordinates:
                order_distance = round(distance.distance(order_coordinates, restaurant_coordinates).km, 2)
            else:
                order_distance = None
            restaurants_with_distance.append((restaurant, order_distance))

        order.restaurants_with_distance = sorted(
            restaurants_with_distance,
            key=lambda item: (item[1] is None, item[1]),
        )

    return render(request, 'order_items.html', {
        'order_items': order_items,
    })
