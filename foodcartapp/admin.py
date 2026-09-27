from collections import defaultdict

from django.contrib import admin
from django.shortcuts import reverse
from django.templatetags.static import static
from django.utils.html import format_html
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .models import Product
from .models import ProductCategory
from .models import Restaurant
from .models import RestaurantMenuItem
from .models import Order
from .models import OrderItem


class RestaurantMenuItemInline(admin.TabularInline):
    model = RestaurantMenuItem
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    search_fields = [
        'name',
        'address',
        'contact_phone',
    ]
    list_display = [
        'name',
        'address',
        'contact_phone',
    ]
    inlines = [
        RestaurantMenuItemInline
    ]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'get_image_list_preview',
        'name',
        'category',
        'price',
    ]
    list_display_links = [
        'name',
    ]
    list_filter = [
        'category',
    ]
    search_fields = [
        # FIXME SQLite can not convert letter case for cyrillic words properly, so search will be buggy.
        # Migration to PostgreSQL is necessary
        'name',
        'category__name',
    ]

    inlines = [
        RestaurantMenuItemInline
    ]
    fieldsets = (
        ('Общее', {
            'fields': [
                'name',
                'category',
                'image',
                'get_image_preview',
                'price',
            ]
        }),
        ('Подробно', {
            'fields': [
                'special_status',
                'description',
            ],
            'classes': [
                'wide'
            ],
        }),
    )

    readonly_fields = [
        'get_image_preview',
    ]

    class Media:
        css = {
            "all": (
                static("admin/foodcartapp.css")
            )
        }

    def get_image_preview(self, obj):
        if not obj.image:
            return 'выберите картинку'
        return format_html('<img src="{url}" style="max-height: 200px;"/>', url=obj.image.url)
    get_image_preview.short_description = 'превью'

    def get_image_list_preview(self, obj):
        if not obj.image or not obj.id:
            return 'нет картинки'
        edit_url = reverse('admin:foodcartapp_product_change', args=(obj.id,))
        return format_html('<a href="{edit_url}"><img src="{src}" style="max-height: 50px;"/></a>', edit_url=edit_url, src=obj.image.url)
    get_image_list_preview.short_description = 'превью'


@admin.register(ProductCategory)
class ProductAdmin(admin.ModelAdmin):
    pass


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [
        OrderItemInline,
    ]
    list_display = [
        'id',
        'status',
        'payment_method',
        'restaurant',
        'firstname',
        'lastname',
        'phonenumber',
        'address',
        'registered_at',
    ]
    fields = [
        'firstname',
        'lastname',
        'phonenumber',
        'address',
        'status',
        'payment_method',
        'restaurant',
        'comment',
        'registered_at',
        'called_at',
        'delivered_at',
    ]
    readonly_fields = ['registered_at']

    def save_model(self, request, obj, form, change):
        if obj.restaurant and obj.status == Order.STATUS_PENDING:
            obj.status = Order.STATUS_COOKING
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        for order_item_form in formset.forms:
            order_item = order_item_form.instance
            if order_item.pk is None and order_item.product_id:
                order_item.price = order_item.product.price
        super().save_formset(request, form, formset, change)

    def response_change(self, request, obj):
        next_url = request.GET.get('next')
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return super().response_change(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'restaurant':
            object_id = None
            if request.resolver_match is not None:
                object_id = request.resolver_match.kwargs.get('object_id')
            order = None
            if object_id:
                order = Order.objects.prefetch_related('items__product').filter(pk=object_id).first()
            if order is not None:
                menu_items = RestaurantMenuItem.objects.filter(availability=True).select_related('restaurant')
                restaurants_by_product = defaultdict(set)
                for menu_item in menu_items:
                    restaurants_by_product[menu_item.product_id].add(menu_item.restaurant)
                product_ids = {item.product_id for item in order.items.all()}
                restaurant_sets = [restaurants_by_product.get(pid, set()) for pid in product_ids]
                available = set.intersection(*restaurant_sets) if restaurant_sets else set()
                kwargs['queryset'] = Restaurant.objects.filter(id__in=[r.id for r in available])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
