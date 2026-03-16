from django.contrib import admin
from .models import Item, StockTransaction


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("item_code", "item_name", "category", "unit", "current_stock", "min_stock")
    search_fields = ("item_code", "item_name")
    list_filter = ("category",)


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "item", "transaction_type", "quantity", "reference_no")
    search_fields = ("item__item_name", "reference_no", "supplier", "requested_by")
    list_filter = ("transaction_type", "date")