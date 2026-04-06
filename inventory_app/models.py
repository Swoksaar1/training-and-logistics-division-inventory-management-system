from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Item(models.Model):
    CATEGORY_CHOICES = [
        ("OFFICE_SUPPLY", "Office Supply Inventory"),
        ("JANITORIAL", "Janitorial Inventory"),
        ("EQUIPMENT", "Equipment Inventory"),
    ]

    CONDITION_CHOICES = [
        ("GOOD", "In Good Condition"),
        ("DAMAGED", "Damaged"),
        ("LOST", "Lost"),
    ]

    item_code = models.CharField(max_length=30, unique=True, blank=True)
    item_name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    unit = models.CharField(max_length=30)
    current_stock = models.PositiveIntegerField(default=0)
    min_stock = models.PositiveIntegerField(default=0)

    life_span = models.CharField(max_length=100, blank=True, null=True)
    condition_status = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        blank=True,
        null=True,
    )

    inventory_custodian_slip = models.CharField(max_length=150, blank=True, null=True)
    material_receipt = models.CharField(max_length=150, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def stock_status(self):
        if self.current_stock == 0:
            return "OUT_OF_STOCK"
        elif self.current_stock <= self.min_stock:
            return "LOW_STOCK"
        return "IN_STOCK"

    def save(self, *args, **kwargs):
        if self.category != "EQUIPMENT":
            self.life_span = None
            self.condition_status = None
            self.inventory_custodian_slip = None
            self.material_receipt = None

        if not self.item_code:
            if self.category == "OFFICE_SUPPLY":
                prefix = "OS"
            elif self.category == "JANITORIAL":
                prefix = "JN"
            elif self.category == "EQUIPMENT":
                prefix = "EQ"
            else:
                prefix = "IT"

            last_item = (
                Item.objects.filter(item_code__startswith=prefix)
                .order_by("-id")
                .first()
            )

            if last_item and last_item.item_code:
                try:
                    last_num = int(last_item.item_code.split("-")[-1])
                except ValueError:
                    last_num = 0
            else:
                last_num = 0

            self.item_code = f"{prefix}-{last_num + 1:04d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} ({self.item_code})"


class StockTransaction(models.Model):
    TRANSACTION_CHOICES = [
        ("IN", "Stock In"),
        ("OUT", "Stock Out"),
        ("BROUGHT_BACK", "Brought Back"),
    ]

    CONDITION_CHOICES = [
        ("GOOD", "In Good Condition"),
        ("DAMAGED", "Damaged"),
        ("LOST", "Lost"),
    ]

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_CHOICES)
    date = models.DateField()
    quantity = models.PositiveIntegerField()

    supplier = models.CharField(max_length=150, blank=True, null=True)

    requested_by = models.CharField(max_length=150, blank=True, null=True)
    approved_by = models.CharField(max_length=150, blank=True, null=True)
    department = models.CharField(max_length=150, blank=True, null=True)

    reference_no = models.CharField(max_length=100, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    inventory_custodian_slip = models.CharField(max_length=150, blank=True, null=True)
    material_requisition = models.CharField(max_length=150, blank=True, null=True)
    property_return_slip_date = models.DateField(blank=True, null=True)
    return_condition_status = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        blank=True,
        null=True,
    )
    life_span = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than 0.")

        if self.transaction_type not in ["IN", "OUT", "BROUGHT_BACK"]:
            raise ValidationError("Transaction type must be IN, OUT, or BROUGHT_BACK.")

        if self.transaction_type == "BROUGHT_BACK" and self.item_id:
            if self.item.category != "EQUIPMENT":
                raise ValidationError(
                    "Brought back transactions are only allowed for equipment items."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            item = Item.objects.select_for_update().get(pk=self.item_id)

            if self.transaction_type == "OUT":
                item.current_stock += self.quantity
            elif self.transaction_type in ["IN", "BROUGHT_BACK"]:
                item.current_stock = max(0, item.current_stock - self.quantity)

            item.save()
            super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type} - {self.item.item_name} ({self.quantity})"


class Profile(models.Model):
    ROLE_CHOICES = (
        ("ADMIN", "Administrator"),
        ("USER", "User"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="USER")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)