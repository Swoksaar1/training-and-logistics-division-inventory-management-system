from django.db import transaction
from rest_framework import serializers
from .models import Item, StockTransaction


def normalize_category(value):
    if value in [None, ""]:
        return value

    raw = str(value).strip().upper().replace(" ", "_")

    category_map = {
        "OFFICE_SUPPLY": "OFFICE_SUPPLY",
        "OFFICE_SUPPLY_INVENTORY": "OFFICE_SUPPLY",
        "JANITORIAL": "JANITORIAL",
        "JANITORIAL_INVENTORY": "JANITORIAL",
        "EQUIPMENT": "EQUIPMENT",
        "EQUIPMENT_INVENTORY": "EQUIPMENT",
    }

    return category_map.get(raw)


def normalize_condition(value):
    if value in [None, ""]:
        return None

    raw = str(value).strip().upper().replace(" ", "_")

    condition_map = {
        "GOOD": "GOOD",
        "IN_GOOD_CONDITION": "GOOD",
        "GOOD_CONDITION": "GOOD",
        "DAMAGED": "DAMAGED",
        "DAMAGE": "DAMAGED",
        "LOST": "LOST",
    }

    return condition_map.get(raw)


class ItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    stock_status = serializers.SerializerMethodField()
    inventory_type = serializers.SerializerMethodField()
    stock = serializers.IntegerField(source="current_stock", read_only=True)
    name = serializers.CharField(source="item_name", read_only=True)
    condition_label = serializers.SerializerMethodField()

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
            "life_span",
            "condition_status",
            "condition_label",
            "inventory_custodian_slip",
            "material_receipt",
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

    def get_condition_label(self, obj):
        return obj.get_condition_status_display() if obj.condition_status else "-"

    def validate_category(self, value):
        normalized = normalize_category(value)
        if not normalized:
            raise serializers.ValidationError(
                "Invalid category. Use OFFICE_SUPPLY, JANITORIAL, or EQUIPMENT."
            )
        return normalized

    def validate_condition_status(self, value):
        if value in [None, ""]:
            return None

        normalized = normalize_condition(value)
        if not normalized:
            raise serializers.ValidationError(
                "Invalid condition status. Use GOOD, DAMAGED, or LOST."
            )
        return normalized

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

    def validate_id(self, value):
        if value is None:
            return value
        if int(value) <= 0:
            raise serializers.ValidationError("ID must be a positive integer.")
        return int(value)

    def validate(self, attrs):
        category = attrs.get("category", getattr(self.instance, "category", None))

        if category != "EQUIPMENT":
            attrs["life_span"] = None
            attrs["condition_status"] = None
            attrs["inventory_custodian_slip"] = None
            attrs["material_receipt"] = None

        return attrs

    def to_internal_value(self, data):
        data = data.copy()

        if "inventory_type" in data and "category" not in data:
            data["category"] = data.get("inventory_type")

        if "name" in data and "item_name" not in data:
            data["item_name"] = data.get("name")

        if "stock" in data and "current_stock" not in data:
            data["current_stock"] = data.get("stock")

        if "status" in data and "condition_status" not in data:
            data["condition_status"] = data.get("status")

        if "item_status" in data and "condition_status" not in data:
            data["condition_status"] = data.get("item_status")

        if "lifeSpan" in data and "life_span" not in data:
            data["life_span"] = data.get("lifeSpan")

        if "lifespan" in data and "life_span" not in data:
            data["life_span"] = data.get("lifespan")

        if "inventoryCustodianSlip" in data and "inventory_custodian_slip" not in data:
            data["inventory_custodian_slip"] = data.get("inventoryCustodianSlip")

        if "materialReceipt" in data and "material_receipt" not in data:
            data["material_receipt"] = data.get("materialReceipt")

        if "current_stock" in data and data.get("current_stock") in ["", None]:
            data["current_stock"] = 0

        if "min_stock" in data and data.get("min_stock") in ["", None]:
            data["min_stock"] = 0

        if "id" in data and data.get("id") in ["", None]:
            data.pop("id", None)

        return super().to_internal_value(data)


class StockTransactionSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.item_name", read_only=True)
    item_code = serializers.CharField(source="item.item_code", read_only=True)
    unit = serializers.CharField(source="item.unit", read_only=True)
    category = serializers.CharField(source="item.get_category_display", read_only=True)
    type_label = serializers.SerializerMethodField()
    return_condition_label = serializers.SerializerMethodField()

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
            "type_label",
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
            "inventory_custodian_slip",
            "material_requisition",
            "property_return_slip_date",
            "return_condition_status",
            "return_condition_label",
            "life_span",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_type_label(self, obj):
        return obj.get_transaction_type_display()

    def get_return_condition_label(self, obj):
        return obj.get_return_condition_status_display() if obj.return_condition_status else "-"

    def validate_transaction_type(self, value):
        if value in [None, ""]:
            raise serializers.ValidationError("Transaction type is required.")

        raw = str(value).strip().upper().replace(" ", "_")

        mapping = {
            "IN": "IN",
            "STOCK_IN": "IN",
            "OUT": "OUT",
            "STOCK_OUT": "OUT",
            "BROUGHT_BACK": "BROUGHT_BACK",
            "BACK": "BROUGHT_BACK",
            "RETURN": "BROUGHT_BACK",
        }

        normalized = mapping.get(raw)
        if not normalized:
            raise serializers.ValidationError("Transaction type must be IN, OUT, or BROUGHT_BACK.")
        return normalized

    def validate_return_condition_status(self, value):
        if value in [None, ""]:
            return None

        normalized = normalize_condition(value)
        if not normalized:
            raise serializers.ValidationError("Invalid return condition status.")
        return normalized

    def validate(self, data):
        transaction_type = data.get(
            "transaction_type",
            getattr(self.instance, "transaction_type", None)
        )
        item = data.get("item", getattr(self.instance, "item", None))
        quantity = data.get("quantity", getattr(self.instance, "quantity", 0))

        if quantity <= 0:
            raise serializers.ValidationError(
                {"quantity": "Quantity must be greater than 0."}
            )

        if transaction_type == "BROUGHT_BACK" and item and item.category != "EQUIPMENT":
            raise serializers.ValidationError(
                {"item": "Brought back is only for equipment items."}
            )

        return data

    def to_internal_value(self, data):
        data = data.copy()

        if "type" in data and "transaction_type" not in data:
            data["transaction_type"] = data.get("type")

        if "status" in data and "return_condition_status" not in data:
            data["return_condition_status"] = data.get("status")

        if "prs_date" in data and "property_return_slip_date" not in data:
            data["property_return_slip_date"] = data.get("prs_date")

        if "prsDate" in data and "property_return_slip_date" not in data:
            data["property_return_slip_date"] = data.get("prsDate")

        if "ics" in data and "inventory_custodian_slip" not in data:
            data["inventory_custodian_slip"] = data.get("ics")

        if "mr" in data and "material_requisition" not in data:
            data["material_requisition"] = data.get("mr")

        if "lifeSpan" in data and "life_span" not in data:
            data["life_span"] = data.get("lifeSpan")

        return super().to_internal_value(data)

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

        item = validated_data["item"]
        qty = validated_data["quantity"]
        tx_type = validated_data["transaction_type"]

        with transaction.atomic():
            item = Item.objects.select_for_update().get(pk=item.pk)

            if tx_type == "OUT":
                if item.current_stock < qty:
                    raise serializers.ValidationError(
                        {"quantity": f"Not enough stock. Available stock: {item.current_stock}"}
                    )
                item.current_stock -= qty

            elif tx_type in ["IN", "BROUGHT_BACK"]:
                item.current_stock += qty

            item.save()

            transaction_obj = StockTransaction.objects.create(**validated_data)

        return transaction_obj

    def update(self, instance, validated_data):
        notes = validated_data.pop("notes", None)
        released_by = validated_data.pop("released_by", None)
        received_by = validated_data.pop("received_by", None)

        if notes is not None and not validated_data.get("remarks"):
            validated_data["remarks"] = notes

        if received_by and not validated_data.get("supplier"):
            validated_data["supplier"] = received_by

        if released_by and not validated_data.get("approved_by"):
            validated_data["approved_by"] = released_by

        new_item = validated_data.get("item", instance.item)
        new_qty = validated_data.get("quantity", instance.quantity)
        new_type = validated_data.get("transaction_type", instance.transaction_type)

        with transaction.atomic():
            old_item = Item.objects.select_for_update().get(pk=instance.item.pk)

            if new_item.pk == old_item.pk:
                target_item = old_item
            else:
                target_item = Item.objects.select_for_update().get(pk=new_item.pk)

            # Reverse old transaction effect
            if instance.transaction_type == "OUT":
                old_item.current_stock += instance.quantity
            elif instance.transaction_type in ["IN", "BROUGHT_BACK"]:
                if old_item.current_stock < instance.quantity:
                    raise serializers.ValidationError(
                        {"detail": "Cannot reverse old transaction because stock would become negative."}
                    )
                old_item.current_stock -= instance.quantity

            # Apply new transaction effect
            if new_type == "OUT":
                if target_item.current_stock < new_qty:
                    raise serializers.ValidationError(
                        {"quantity": f"Not enough stock. Available stock: {target_item.current_stock}"}
                    )
                target_item.current_stock -= new_qty

            elif new_type in ["IN", "BROUGHT_BACK"]:
                target_item.current_stock += new_qty

            old_item.save()
            if target_item.pk != old_item.pk:
                target_item.save()

            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            instance.item = target_item
            instance.save()

        return instance