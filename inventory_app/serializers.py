from rest_framework import serializers
from .models import Item, StockTransaction


class ItemSerializer(serializers.ModelSerializer):
    stock_status = serializers.SerializerMethodField()
    inventory_type = serializers.SerializerMethodField()
    stock = serializers.IntegerField(source="current_stock", read_only=True)
    name = serializers.CharField(source="item_name", read_only=True)

    class Meta:
        model = Item
        fields = [
            "id",
            "item_code",
            "item_name",
            "name",
            "description",
            "category",
            "inventory_type",
            "unit",
            "current_stock",
            "stock",
            "min_stock",
            "stock_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "item_code",
            "created_at",
            "updated_at",
        ]

    def get_stock_status(self, obj):
        return obj.stock_status()

    def get_inventory_type(self, obj):
        return obj.get_category_display()

    def validate_category(self, value):
        if not value:
            raise serializers.ValidationError("Category is required.")

        normalized = str(value).strip().upper().replace(" ", "_")

        category_map = {
            "OFFICE_SUPPLY": "OFFICE_SUPPLY",
            "OFFICE_SUPPLY_INVENTORY": "OFFICE_SUPPLY",
            "JANITORIAL": "JANITORIAL",
            "JANITORIAL_INVENTORY": "JANITORIAL",
            "EQUIPMENT": "EQUIPMENT",
            "EQUIPMENT_INVENTORY": "EQUIPMENT",
        }

        if normalized in category_map:
            return category_map[normalized]

        raise serializers.ValidationError(
            "Invalid category. Use OFFICE_SUPPLY, JANITORIAL, or EQUIPMENT."
        )

    def validate_current_stock(self, value):
        if value is None:
            return 0
        if int(value) < 0:
            raise serializers.ValidationError("Current stock cannot be negative.")
        return int(value)

    def validate_min_stock(self, value):
        if value is None:
            return 0
        if int(value) < 0:
            raise serializers.ValidationError("Minimum stock cannot be negative.")
        return int(value)

    def to_internal_value(self, data):
        data = data.copy()

        if "inventory_type" in data and "category" not in data:
            data["category"] = data.get("inventory_type")

        if "name" in data and "item_name" not in data:
            data["item_name"] = data.get("name")

        if "stock" in data and "current_stock" not in data:
            data["current_stock"] = data.get("stock")

        if data.get("current_stock") in ["", None]:
            data["current_stock"] = 0

        if data.get("min_stock") in ["", None]:
            data["min_stock"] = 0

        return super().to_internal_value(data)


class StockTransactionSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.item_name", read_only=True)
    item_code = serializers.CharField(source="item.item_code", read_only=True)
    unit = serializers.CharField(source="item.unit", read_only=True)
    category = serializers.CharField(source="item.get_category_display", read_only=True)

    notes = serializers.CharField(write_only=True, required=False, allow_blank=True)
    released_by = serializers.CharField(write_only=True, required=False, allow_blank=True)
    received_by = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = StockTransaction
        fields = [
            "id",
            "item",
            "item_name",
            "item_code",
            "category",
            "unit",
            "transaction_type",
            "date",
            "quantity",
            "supplier",
            "requested_by",
            "approved_by",
            "department",
            "reference_no",
            "remarks",
            "notes",
            "released_by",
            "received_by",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate(self, data):
        transaction_type = data.get("transaction_type")
        item = data.get("item")
        quantity = data.get("quantity", 0)

        if quantity <= 0:
            raise serializers.ValidationError(
                {"quantity": "Quantity must be greater than 0."}
            )

        if transaction_type not in ["IN", "OUT"]:
            raise serializers.ValidationError(
                {"transaction_type": "Transaction type must be IN or OUT."}
            )

        if transaction_type == "OUT" and item and quantity > item.current_stock:
            raise serializers.ValidationError(
                {"quantity": "Not enough stock available."}
            )

        return data

    def create(self, validated_data):
        notes = validated_data.pop("notes", None)
        released_by = validated_data.pop("released_by", None)
        received_by = validated_data.pop("received_by", None)

        if notes is not None and not validated_data.get("remarks"):
            validated_data["remarks"] = notes

        if received_by and not validated_data.get("supplier"):
            validated_data["supplier"] = received_by

        if released_by and not validated_data.get("approved_by"):
            validated_data["approved_by"] = released_by

        return super().create(validated_data)

    def update(self, instance, validated_data):
        raise serializers.ValidationError(
            {"detail": "Updating transactions is disabled to protect stock integrity."}
        )