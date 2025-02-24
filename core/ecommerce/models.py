from django.db import models
from userManage.models import CustomUser
from django.utils.text import slugify

class Categorys(models.Model):
    category_name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(unique=True,blank=True)
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories'
    )
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.category_name)
            original_slug = self.slug
            counter = 1
            while Categorys.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.category_name

class Store(models.Model):
    store_name = models.CharField(max_length=155)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='store_owner')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_profit = models.DecimalField(max_digits=12,decimal_places=2, default=0.00)
    monthly_profit = models.DecimalField(max_digits=12,decimal_places=2, default=0.00)
    total_sales = models.IntegerField(default=0)

    def __str__(self):
        return self.store_name    

class Products(models.Model):
    product_name = models.CharField(max_length=155)
    sku = models.CharField(max_length=50)
    product_category = models.ForeignKey(Categorys, on_delete=models.DO_NOTHING)
    short_description = models.CharField(max_length=255)
    product_description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    def __str__(self):
        return self.product_name

class VariantOptions(models.Model):
    options_name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.ForeignKey(Categorys, on_delete=models.CASCADE, null=True,blank=True)

    def __str__(self):
        return self.options_name
    
class VariantValues(models.Model):
    value = models.CharField(max_length=155)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.value

class Variants(models.Model):
    variant_options = models.ForeignKey(VariantOptions, on_delete=models.CASCADE)
    variant_values = models.ForeignKey(VariantValues, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.variant_options} - {self.variant_values}"

class ProductVariants(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='product_variant')
    variants = models.ManyToManyField(Variants)
    other_variants = models.JSONField(null=True,blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=1)
    def __str__(self):
        return f"{self.product.product_name} - {self.variants.all()}"



#----------------------------------------------------------------------------------------------------------

class Address(models.Model):
    class AddressTypeChoice(models.TextChoices):
        SHOPPING = "Shopping_address", "Shopping Address"
        BILING = "Biling_address", "Biling Address"

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,related_name='user_address')
    address_type = models.CharField(
        max_length=16,
        choices=AddressTypeChoice.choices
    )
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)



class Order(models.Model):
    class OrderStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELED = "CANCELED", "Canceled"
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="orders")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, related_name="shipping_orders"
    )
    billing_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, related_name="billing_orders"
    )

    def __str__(self):
        return f"Order {self.id} - {self.user.username} - {self.get_status_display()}"
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_variant = models.ForeignKey(ProductVariants, on_delete=models.CASCADE, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product_variant.product.product_name} (Order {self.order.id})"
    
#----------------------------------------------------------------------------------------------------

class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart - {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product_variant = models.ForeignKey(ProductVariants, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product_variant.product.product_name} in {self.cart.user.username}'s cart"
    
class Review(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveIntegerField(default=1)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")

    def __str__(self):
        return f"Review by {self.user.username} on {self.product.product_name} - {self.rating}/5"