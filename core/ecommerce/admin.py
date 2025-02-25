from django.contrib import admin
from .models import Products,ProductVariants,VariantOptions,VariantValues,Categorys,Variants
from .models import Address,Order,OrderItem,Cart,CartItem,Review,Store,OrderCancelRecord

admin.site.register(Products)
admin.site.register(ProductVariants)
admin.site.register(VariantOptions)
admin.site.register(VariantValues)
admin.site.register(Categorys)
admin.site.register(Variants)
admin.site.register(Address)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Review)
admin.site.register(Store)
admin.site.register(OrderCancelRecord)
