from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ItemViewSet,
    StockTransactionViewSet,
    dashboard_summary,
    monthly_summary,
    stock_card,
    me,
    change_password,  # ✅ add this
)

router = DefaultRouter()
router.register(r"items", ItemViewSet, basename="items")
router.register(r"transactions", StockTransactionViewSet, basename="transactions")

urlpatterns = [
    path("", include(router.urls)),

    # ✅ auth endpoints
    path("auth/me/", me, name="auth-me"),
    path("auth/change-password/", change_password, name="change-password"),

    # Custom report/dashboard endpoints
    path("dashboard-summary/", dashboard_summary, name="dashboard-summary"),
    path("reports/monthly-summary/", monthly_summary, name="monthly-summary"),
    path("reports/stock-card/<int:item_id>/", stock_card, name="stock-card"),
]