from django.db.models import Sum, F, Q
from django.db.models.functions import ExtractMonth
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Item, StockTransaction
from .serializers import ItemSerializer, StockTransactionSerializer


def normalize_category_filter(value):
    if not value:
        return None

    raw = str(value).strip().upper().replace(" ", "_")
    category_map = {
        "OFFICE_SUPPLY": "OFFICE_SUPPLY",
        "OFFICE_SUPPLY_INVENTORY": "OFFICE_SUPPLY",
        "JANITORIAL": "JANITORIAL",
        "JANITORIAL_INVENTORY": "JANITORIAL",
        "EQUIPMENT": "EQUIPMENT",
        "EQUIPMENT_INVENTORY": "EQUIPMENT",
        "ALL": None,
    }
    return category_map.get(raw, raw)


def normalize_transaction_filter(value):
    if not value:
        return None

    raw = str(value).strip().upper().replace(" ", "_")
        "IN": "IN",
        "STOCK_IN": "IN",
        "OUT": "OUT",
        "STOCK_OUT": "OUT",
        "BROUGHT_BACK": "BROUGHT_BACK",
        "BACK": "BROUGHT_BACK",
        "RETURN": "BROUGHT_BACK",
        "ALL": None,
        "ALL_TYPES": None,
    }
    return mapping.get(raw, raw)


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all().order_by("-id")
    serializer_class = ItemSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        category = (
            self.request.query_params.get("category")
            or self.request.query_params.get("inventory_type")
        )
        search = self.request.query_params.get("search")

        mapped_category = normalize_category_filter(category)
        if mapped_category:
            qs = qs.filter(category=mapped_category)

        if search:
            qs = qs.filter(
                Q(item_name__icontains=search)
                | Q(item_code__icontains=search)
                | Q(description__icontains=search)
                | Q(life_span__icontains=search)
            )

        return qs


class StockTransactionViewSet(viewsets.ModelViewSet):
    queryset = StockTransaction.objects.select_related("item").all().order_by("-date", "-id")
    serializer_class = StockTransactionSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        transaction_type = (
            self.request.query_params.get("transaction_type")
            or self.request.query_params.get("type")
        )
        item_id = self.request.query_params.get("item")
        search = self.request.query_params.get("search")
        category = (
            self.request.query_params.get("category")
            or self.request.query_params.get("inventory_type")
        )

        mapped_type = normalize_transaction_filter(transaction_type)
        if mapped_type:
            qs = qs.filter(transaction_type=mapped_type)

        mapped_category = normalize_category_filter(category)
        if mapped_category:
            qs = qs.filter(item__category=mapped_category)

        if item_id:
            qs = qs.filter(item_id=item_id)

        if search:
            qs = qs.filter(
                Q(item__item_name__icontains=search)
                | Q(item__item_code__icontains=search)
                | Q(requested_by__icontains=search)
                | Q(approved_by__icontains=search)
                | Q(supplier__icontains=search)
                | Q(remarks__icontains=search)
                | Q(inventory_custodian_slip__icontains=search)
                | Q(material_requisition__icontains=search)
            )

        return qs


@api_view(["GET"])
def dashboard_summary(request):
    today = request.GET.get("date") or str(timezone.localdate())

    items = Item.objects.all()

    total_items = items.count()
    office_supply_count = items.filter(category="OFFICE_SUPPLY").count()
    janitorial_count = items.filter(category="JANITORIAL").count()
    equipment_count = items.filter(category="EQUIPMENT").count()

    low_stock_count = items.filter(
        current_stock__gt=0,
        current_stock__lte=F("min_stock"),
    ).count()
    out_of_stock_count = items.filter(current_stock=0).count()

    good_condition_count = items.filter(
        category="EQUIPMENT",
        condition_status="GOOD",
    ).count()
    damaged_count = items.filter(
        category="EQUIPMENT",
        condition_status="DAMAGED",
    ).count()
    lost_count = items.filter(
        category="EQUIPMENT",
        condition_status="LOST",
    ).count()

    stock_in_today = StockTransaction.objects.filter(
        transaction_type="IN",
        date=today,
    ).count()

    stock_out_today = StockTransaction.objects.filter(
        transaction_type="OUT",
        date=today,
    ).count()

    brought_back_today = StockTransaction.objects.filter(
        transaction_type="BROUGHT_BACK",
        date=today,
    ).count()

    total_stock_in = (
        StockTransaction.objects.filter(transaction_type="IN").aggregate(total=Sum("quantity"))["total"] or 0
    )
    total_stock_out = (
        StockTransaction.objects.filter(transaction_type="OUT").aggregate(total=Sum("quantity"))["total"] or 0
    )
    total_brought_back = (
        StockTransaction.objects.filter(transaction_type="BROUGHT_BACK").aggregate(total=Sum("quantity"))["total"] or 0
    )

    recent_transactions = StockTransaction.objects.select_related("item").order_by("-date", "-id")[:10]
    recent_data = StockTransactionSerializer(recent_transactions, many=True).data

    return Response(
        {
            "total_items": total_items,
            "office_supply_count": office_supply_count,
            "janitorial_count": janitorial_count,
            "equipment_count": equipment_count,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "good_condition_count": good_condition_count,
            "damaged_count": damaged_count,
            "lost_count": lost_count,
            "stock_in_today": stock_in_today,
            "stock_out_today": stock_out_today,
            "brought_back_today": brought_back_today,
            "total_stock_in": total_stock_in,
            "total_stock_out": total_stock_out,
            "total_brought_back": total_brought_back,
            "recent_transactions": recent_data,
        }
    )


@api_view(["GET"])
def monthly_summary(request):
    year = request.query_params.get("year")
    category = request.query_params.get("category")

    items_qs = Item.objects.all().order_by("item_name")

    mapped_category = normalize_category_filter(category)
    if mapped_category:
        items_qs = items_qs.filter(category=mapped_category)

    result = []

    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
    }

    year_int = None
    if year:
        try:
            year_int = int(year)
        except ValueError:
            return Response(
                {"error": "Invalid year parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )

    for item in items_qs:
        txns = item.transactions.all()

        if year_int is not None:
            txns = txns.filter(date__year=year_int)

        monthly_data = {
            m: {"IN": 0, "OUT": 0, "BROUGHT_BACK": 0}
            for m in range(1, 13)
        }

        aggregates = (
            txns.annotate(month=ExtractMonth("date"))
            .values("month", "transaction_type")
            .annotate(total_qty=Sum("quantity"))
            .order_by("month")
        )

        for row in aggregates:
            month = row["month"]
            tx_type = row["transaction_type"]
            total_qty = row["total_qty"] or 0
            if month in monthly_data and tx_type in ["IN", "OUT", "BROUGHT_BACK"]:
                monthly_data[month][tx_type] = total_qty

        monthly_formatted = {month_names[m]: monthly_data[m] for m in range(1, 13)}

        result.append(
            {
                "item_id": item.id,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "category": item.get_category_display(),
                "unit": item.unit,
                "current_stock": item.current_stock,
                "min_stock": item.min_stock,
                "stock_status": item.stock_status(),
                "life_span": item.life_span,
                "condition_status": item.condition_status,
                "condition_label": item.get_condition_status_display() if item.condition_status else "-",
                "monthly": monthly_formatted,
            }
        )

    return Response(result)


@api_view(["GET"])
def stock_card(request, item_id):
    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        return Response({"error": "Item not found."}, status=status.HTTP_404_NOT_FOUND)

    transactions = item.transactions.all().order_by("date", "id")
    tx_data = StockTransactionSerializer(transactions, many=True).data

    return Response(
        {
            "item": ItemSerializer(item).data,
            "transactions": tx_data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    role = getattr(getattr(u, "profile", None), "role", "USER")
    name = (u.first_name + " " + u.last_name).strip() or u.username
    is_active = u.is_active and getattr(getattr(u, "profile", None), "is_active", True)

    return Response(
        {
            "id": u.id,
            "username": u.username,
            "name": name,
            "role": role,
            "is_active": is_active,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    current_password = request.data.get("current_password", "")
    new_password = request.data.get("new_password", "")

    if not current_password or not new_password:
        return Response({"error": "Missing password fields."}, status=400)

    user = request.user

    if not user.check_password(current_password):
        return Response({"error": "Current password is incorrect."}, status=400)

    if len(new_password) < 8:
        return Response({"error": "New password must be at least 8 characters."}, status=400)

    user.set_password(new_password)
    user.save()

    return Response({"detail": "Password updated."})