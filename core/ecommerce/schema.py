import graphene
from graphene_django import DjangoObjectType
from .models import (
    Categorys, Products, VariantOptions, VariantValues, Variants, ProductVariants,
    Address, Order, OrderItem, Cart, CartItem, Review
)
from django.db import transaction
from graphene import relay
from graphql_relay.node.node import from_global_id
from graphene_django.filter import DjangoFilterConnectionField
from graphene.types.generic import GenericScalar
from decimal import Decimal

class categoryType(DjangoObjectType):
    category_path = graphene.String()
    class Meta:
        model = Categorys
        fields = '__all__'

    def resolve_category_path(Self, info):
        path = []
        category = Self
        seen_categories = set()

        while category:
            if category in seen_categories:
                break

            seen_categories.add(category)
            path.append(category.slug)
            category = category.parent_category

        return "/".join(path[::-1])

class CategoryNode(DjangoObjectType):
    class Meta:
        model = Categorys
        interfaces = (relay.Node,)
        fields = '__all__'
        filter_fields = {
            'category_name': ['exact', 'icontains'],
            'parent_category__category_name': ['exact', 'icontains'],
            'slug': ['exact', 'icontains'],
        }

class ProductNode(DjangoObjectType):
    class Meta:
        model = Products
        interfaces = (graphene.relay.Node,)
        fields = '__all__'
        filter_fields = {
            'product_name': ['exact', 'icontains'],
            'sku': ['exact', 'icontains'],
            'short_description': ['exact', 'icontains'],
            'created_at': ['exact', 'lt', 'gt'],
            'updated_at': ['exact', 'lt', 'gt'],
            'product_category__category_name': ['exact', 'icontains'],
            'created_by__username': ['exact', 'icontains'],
        }

class variant_optionsType(DjangoObjectType):
    class Meta:
        model = VariantOptions
        fields = '__all__'

class variant_valuesType(DjangoObjectType):
    class Meta:
        model = VariantValues
        fields = '__all__'

class variantsType(DjangoObjectType):
    class Meta:
        model = Variants
        fields = '__all__'
class VariantNode(DjangoObjectType):
    class Meta:
        model = Variants
        interfaces = (relay.Node,)
class AddressType(DjangoObjectType):
    class Meta:
        model = Address
        fields = '__all__'

class OrderNode(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (relay.Node,)


class OrderItemType(DjangoObjectType):
    class Meta:
        model = OrderItem
        fields = '__all__'
class CartType(DjangoObjectType):
    class Meta:
        model = Cart
        fields = '__all__'
class CartItemType(DjangoObjectType):
    class Meta:
        model = CartItem
        fields = '__all__'

class ProductVariantNode(DjangoObjectType):
    variants = graphene.Field(GenericScalar)
    other_variants = graphene.Field(GenericScalar)

    class Meta:
        model = ProductVariants
        filter_fields = {
            "id": ["exact"],
            "variants__variant_options__options_name": ["exact", "icontains"],
            "variants__variant_values__value": ["exact", "icontains"],
            "price": ["exact", "lt", "lte", "gt", "gte"],
            "product":{"exact"},
        }
        interfaces = (relay.Node,)

    def resolve_variants(self, info):
        variants_dict = {}

        variants = self.variants.all()
        if not variants.exists():
            return variants_dict

        for variant in variants:
            option_name = variant.variant_options.options_name
            value_name = variant.variant_values.value
            variants_dict[option_name] = value_name

        return variants_dict

    def resolve_other_variants(self, info):
        return self.other_variants

class ReviewType(DjangoObjectType):
    class Meta:
        model = Review
        fields = '__all__'
#----------------------------------------------------------------------------------------------

class CreateProductVariantMutation(graphene.Mutation):
    product_variant = graphene.Field(ProductVariantNode)
    class Arguments:
        price = graphene.String(required=True)
        variants= graphene.List(graphene.ID, required=True)
        product = graphene.ID(required=True)
        other_variants = graphene.JSONString(required=False)

    def mutate(Self,info,price,variants,product,other_variants=None):
        variants = Variants.objects.filter(id__in=variants)
        price = Decimal(price)
        product = Products.objects.get(id=product)
        
        existing_variants = ProductVariants.objects.filter(product=product)

        for existing_variant in existing_variants:
            existing_ids = sorted([str(id) for id in existing_variant.variants.values_list('id', flat=True)])
            
            if variants == existing_ids:
                raise Exception('Bu varyasyon kombinasyonu zaten mevcut ', existing_ids )
        product_variant = ProductVariants(price=price, product=product, other_variants=other_variants)
        product_variant.save()

        product_variant.variants.set(variants)

        return CreateProductVariantMutation(product_variant=product_variant)
    
class UpdateProductVariantMutation(graphene.Mutation):
    product_variant = graphene.Field(ProductVariantNode)

    class Arguments:
        product_variant = graphene.ID(required=True)
        price = graphene.String(required=False)
        variants = graphene.List(graphene.ID, required=False)
        other_variants = graphene.JSONString(required=False)

    def mutate(self, info, product_variant, price=None, variants=None, other_variants=None):
        try:
            product_variant = ProductVariants.objects.get(id=product_variant)

            if price:
                product_variant.price = Decimal(price)

            if variants:
                variants = Variants.objects.filter(id__in=variants)
                product_variant.variants.set(variants)

            if other_variants is not None:
                product_variant.other_variants = other_variants

            product_variant.save()

            return UpdateProductVariantMutation(product_variant=product_variant)

        except ProductVariants.DoesNotExist:
            raise Exception("Bu ID'ye sahip bir ürün varyantı bulunamadı.")
        except Exception as e:
            raise Exception(str(e))
        
class DeleteProductVariantMuttion(graphene.Mutation):
    success = graphene.Boolean()
    class Arguments:
        product_variant = graphene.ID()

    def mutate(self,info,product_variant):
        try:
            product_variant = ProductVariants.objects.get(id=product_variant)
            product_variant.delete()
            return DeleteProductVariantMuttion(success=True)
        except Exception as e:
            raise Exception(str(e))
    
class CreateProductMutation(graphene.Mutation):
    product = graphene.Field(ProductNode)
    class Arguments:
        product_name = graphene.String()
        sku = graphene.String()
        product_category = graphene.ID()
        short_description = graphene.String()
        product_description = graphene.String()
    
    def mutate(self,info,product_name,sku,product_category,short_description,product_description):
        try:
            user= info.context.user
            if user.is_anonymous:
                raise Exception('Lütfen giriş yapınız.')
            
            product_category = Categorys.objects.get(id=product_category)

            product = Products(
                product_name=product_name,
                sku=sku,
                product_category=product_category,
                short_description=short_description,
                product_description=product_description,
                created_by = user
            )
            product.save()
            return CreateProductMutation(product=product)
        except Exception as e:
            raise Exception(str(e))
        
class UpdateProductMutation(graphene.Mutation):
    product = graphene.Field(ProductNode)
    success = graphene.Boolean()
    class Arguments:
        product = graphene.ID(required=True)
        product_name = graphene.String(required=False)
        sku = graphene.String(required=False)
        product_category = graphene.ID(required=False)
        short_description = graphene.String(required=False)
        product_description = graphene.String(required=False)

    def mutate(self,info,product,product_name=None,sku=None,product_category=None,short_description=None,product_description=None):
        try:
            user = info.context.user
            if user.is_anonymous:
                raise Exception('Lütfen giriş yapınız.')
            product = Products.objects.get(id=product)

            if product_name:
                product.product_name=product_name
            
            if sku:
                product.sku=sku

            if product_category:
                product_category = Categorys.objects.get(id=product_category)
                product.product_category=product_category
            if short_description:
                product.short_description=short_description
            if product_description:
                product.product_description=product_description

            product.save()

            return UpdateProductMutation(product=product,success=True)
        except Exception as e:
            raise Exception(str(e))

class DeleteProductMutation(graphene.Mutation):
    success = graphene.Boolean()
    class Arguments:
        product= graphene.ID(required=True)
    
    def mutate(self,info,product):
        try:
            user = info.context.user
            if user.is_anonymous:
                raise Exception('Lütfen giriş yapınız.')
            
            resolved_type, resolved_idx = from_global_id(product)

            if resolved_type != "ProductNode":
                raise Exception("Geçersiz ürün ID’si.")
            
            product = Products.objects.get(id=resolved_idx)
            product.delete()
            return DeleteProductVariantMuttion(success=True)
        except Exception as e:
            raise Exception(str(e))

class CreateCategoryMutation(graphene.Mutation):
    category = graphene.Field(categoryType)
    class Arguments:
        category_name = graphene.String(required=True)
        parent_category = graphene.ID(required=False)

    def mutate(self,info,category_name,parent_category=None):
        try:

            category = Categorys(
                category_name=category_name
            )
            if parent_category:
                parent_category = Categorys.objects.get(id=parent_category)
                category.parent_category = parent_category

            category.save()
            return CreateCategoryMutation(category=category)
        except Exception as e:
            raise Exception(str(e))

class UpdateCategoryMutation(graphene.Mutation):
    category = graphene.Field(categoryType)
    success = graphene.Boolean()
    class Arguments:
        category = graphene.ID(required=True)
        category_name = graphene.String(required=False)
        parent_category = graphene.ID(required=False)

    def mutate(self,info,category,category_name=None,parent_category=None):
        try:
            category = Categorys.objects.get(id=category)
            if category_name:
                category.category_name=category_name

            if parent_category:
                parent_category = Categorys.objects.get(id=parent_category)
                category.parent_category=parent_category

            category.save()

            return UpdateCategoryMutation(category=category, success=True)
        except Exception as e:
            raise Exception(str(e))

class DeleteCategoryMutation(graphene.Mutation):
    success = graphene.Boolean()
    class Arguments:
        category = graphene.ID(required=True)

    def mutate(self,info,category):
        try:
            category = Categorys.objects.get(id=category)
            category.delete()
            return  DeleteCategoryMutation(success=True)
        except Exception as e:
            raise Exception(str(e))

class CreateVariantOptionMutation(graphene.Mutation):
    variant_option = graphene.Field(variant_optionsType)
    class Arguments:
        options_name = graphene.String(required=True)
        category = graphene.ID(required=True)

    def mutate(self,info,options_name,category):
        try:
            category = Categorys.objects.get(id=category)
            variant_option = VariantOptions(
                options_name=options_name,
                category=category
            )
            variant_option.save()
            return  CreateVariantOptionMutation(variant_option=variant_option)
        except Exception as e:
            raise Exception(str(e))

class UpdateVariantOptionMutation(graphene.Mutation):
    variant_option = graphene.Field(variant_optionsType)
    success = graphene.Boolean()
    class Arguments:
        variant_option = graphene.ID(required=True)
        options_name = graphene.String(required=False)
        category = graphene.ID(required=False)
    def mutate(self,info,variant_option,options_name=None,category=None):
        try:
            variant_option = VariantOptions.objects.get(id=variant_option)
            if options_name:
                variant_option.options_name=options_name
            if category:
                category = Categorys.objects.get(id=category)
                variant_option.category=category
            variant_option.save()
            return UpdateVariantOptionMutation(variant_option=variant_option,success=True)
        except Exception as e:
            raise Exception(str(e))

class DeleteVariantOptionMutation(graphene.Mutation):
    class Arguments:
        variant_option = graphene.ID(required=True)

    success = graphene.Boolean()

    def mutate(self, info, variant_option):
        try:
            variant_option = VariantOptions.objects.get(id=variant_option)
            variant_option.delete()
            return DeleteVariantOptionMutation(success=True)
        except VariantOptions.DoesNotExist:
            raise Exception("Belirtilen ID'ye sahip varyant seçeneği bulunamadı.")
        except Exception as e:
            raise Exception(str(e))

class CreateVariantValueMutation(graphene.Mutation):
    variant_value = graphene.Field(variant_valuesType)
    class Arguments:
        value = graphene.String(required=True)

    def mutate(self,info,value):
        variant_value = VariantValues(value=value)
        variant_value.save()
        return CreateVariantValueMutation(variant_value=variant_value)

class UpdateVariantValueMutation(graphene.Mutation):
    variant_value = graphene.Field(variant_valuesType)
    success = graphene.Boolean()
    class Arguments:
        variant_value = graphene.ID(required=True)
        value = graphene.String(required=False)

    def mutate(self,info,variant_value,value):
        try:
            variant_value = VariantValues.objects.get(id=variant_value)
            variant_value.value=value
            return UpdateVariantValueMutation(variant_value=variant_value, success=True)
        except Exception as e:
            raise Exception(str(e))

class DeleteVariantValueMutation(graphene.Mutation):
    success = graphene.Boolean()
    class Arguments:
        variant_value = graphene.ID(required=True)
    def mutate(self,info,variant_value):
        try:
            variant_value = VariantValues.objects.get(id=variant_value)
            variant_value.delete()
            return  DeleteVariantValueMutation(success=True)
        except Exception as e:
            raise Exception(str(e))

class CreateVariantMutation(graphene.Mutation):
    variant = graphene.Field(variantsType)
    class Arguments:
        variant_options = graphene.ID(required=True)
        variant_values = graphene.ID(required=True)
    def mutate(self,info,variant_option,variant_values):
        try:
            variant_options = VariantOptions.objects.get(id=variant_option)
            variant_values = VariantValues.objects.get(id=variant_values)
            variant = Variants(
                variant_options=variant_options,
                variant_values=variant_values,
            )
            variant.save()
            return CreateVariantMutation(variant=variant)
        except Exception as e:
            raise Exception(str(e))

class UpdateVariantMutation(graphene.Mutation):
    variant = graphene.Field(variantsType)
    success = graphene.Boolean()
    class Arguments:
        variant = graphene.ID(required=True)
        variant_options = graphene.ID(required=False)
        variant_value = graphene.ID(required=False)
    def mutate(self,info,variant,variant_options=None,variant_values=None):
        try:
            variant = Variants.objects.get(id=variant)
            if variant_options:
                variant_options = VariantOptions.objects.get(id=variant_options)
                variant.variant_options=variant_options
            if variant_values:
                variant_values = VariantValues.objects.get(id=variant_values)
                variant.variant_values_id=variant_values
            variant.save()
            return UpdateVariantMutation(variant=variant, success=True)
        except Exception as e:
            raise Exception(str(e))

class DeleteVariantMutation(graphene.Mutation):
    success=graphene.Boolean()
    class Arguments:
        variant = graphene.ID(required=True)
    def mutate(self,info,variant):
        try:
            variant = Variants.objects.get(id=variant)
            variant.delete()
            return DeleteVariantMutation(success=True)
        except Exception as e:
            raise Exception(str(e))


class CreateAddressMutation(graphene.Mutation):
    address = graphene.Field(AddressType)

    class Arguments:
        address_type = graphene.String(required=True)
        street = graphene.String(required=True)
        city = graphene.String(required=True)
        postal_code = graphene.String(required=True)

    def mutate(self, info, address_type, street, city, postal_code):
        try:
            user = info.context.user
            if user.is_anonymous:
                raise Exception("Lütfen giriş yapınız.")

            address = Address(
                user=user,
                address_type=address_type,
                street=street,
                city=city,
                postal_code=postal_code
            )
            address.save()
            return CreateAddressMutation(address=address)
        except Exception as e:
            raise Exception(str(e))

class UpdateAddressMutation(graphene.Mutation):
    address = graphene.Field(AddressType)

    class Arguments:
        id = graphene.ID(required=True)
        address_type = graphene.String()
        street = graphene.String()
        city = graphene.String()
        postal_code = graphene.String()

    def mutate(self, info, id, address_type=None, street=None, city=None, postal_code=None):
        try:
            address = Address.objects.get(pk=id)
            if Address.DoesNotExist:
                raise Exception("Belirtilen adres bulunamadı.")

            if address_type is not None:
                address.address_type = address_type
            if street is not None:
                address.street = street
            if city is not None:
                address.city = city
            if postal_code is not None:
                address.postal_code = postal_code

            address.save()
            return UpdateAddressMutation(address=address)
        except Exception as e:
            raise Exception(str(e))

class DeleteAddressMutation(graphene.Mutation):
    success = graphene.Boolean()
    class Arguments:
        id = graphene.ID(required=True)

    def mutate(self,info,id):
        try:
            address = Address.objects.get(id=id)
            address.delete()
            return DeleteAddressMutation(success=True)
        except Exception as e:
            raise Exception(str(e))

class AddToCartMutation(graphene.Mutation):
    class Arguments:
        product_variant = graphene.ID(required=True)
        quantity = graphene.Int(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    cart_item = graphene.Field(CartItemType)

    def mutate(self, info, product_variant,quantity):
        user = info.context.user
        if user.is_anonymous:
            raise Exception('Lütfen giriş yapınız.')
        try:
            with transaction.atomic():
                cart, created = Cart.objects.get_or_create(user=user)

                product_variant = ProductVariants.objects.get(id=product_variant)

                if product_variant.stock < quantity:
                    return AddToCartMutation(
                        success=False,
                        message="Not enough stock available"
                    )

                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product_variant=product_variant,
                    defaults={'quantity': quantity}
                )

                if not created:
                    cart_item.quantity += quantity
                    cart_item.save()

                return AddToCartMutation(
                    success=True,
                    message="Product added to cart successfully",
                    cart_item=cart_item
                )

        except ProductVariants.DoesNotExist:
            return AddToCartMutation(
                success=False,
                message="Product variant not found"
            )
        except Exception as e:
            return AddToCartMutation(
                success=False,
                message=str(e)
            )

class UpdateCartItemMutation(graphene.Mutation):
    class Arguments:
        cart_item = graphene.ID(required=True)
        quantity = graphene.Int(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    cart_item = graphene.Field(CartItemType)

    def mutate(self, info, cart_item,quantity):
        try:
            cart_item = CartItem.objects.get(
                id=cart_item,
                cart__user=info.context.user
            )

            if quantity <= 0:
                cart_item.delete()
                return UpdateCartItemMutation(
                    success=True,
                    message="Item removed from cart"
                )

            if cart_item.product_variant.stock < quantity:
                return UpdateCartItemMutation(
                    success=False,
                    message="Not enough stock available"
                )

            cart_item.quantity = quantity
            cart_item.save()

            return UpdateCartItemMutation(
                success=True,
                message="Cart item updated successfully",
                cart_item=cart_item
            )

        except CartItem.DoesNotExist:
            return UpdateCartItemMutation(
                success=False,
                message="Cart item not found"
            )

class CreateOrderMutation(graphene.Mutation):
    class Arguments:
        shipping_address = graphene.ID(required=True)
        billing_address = graphene.ID(required=True)
        status = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    order = graphene.Field(OrderNode)

    def mutate(self, info, shipping_address,billing_address, status):
        user = info.context.user
        if user.is_anonymous:
            raise Exception('Lütfen giriş yapınız.')
        try:
            with transaction.atomic():
                cart = Cart.objects.get(user=user)
                cart_items = cart.items.select_related('product_variant').all()

                if not cart_items.exists():
                    return CreateOrderMutation(
                        success=False,
                        message="Cart is empty"
                    )

                shipping_address = Address.objects.get(
                    id=shipping_address,
                    user=user
                )
                billing_address = Address.objects.get(
                    id=billing_address,
                    user=user
                )

                total_price = sum(
                    item.quantity * item.product_variant.price
                    for item in cart_items
                )

                order = Order.objects.create(
                    user=user,
                    shipping_address=shipping_address,
                    billing_address=billing_address,
                    total_price=total_price,
                    status=status,
                )

                order_items = []
                for cart_item in cart_items:
                    if cart_item.product_variant.stock < cart_item.quantity:
                        raise ValueError(
                            f"Not enough stock for {cart_item.product_variant.product.product_name}"
                        )

                    order_items.append(OrderItem(
                        order=order,
                        product_variant=cart_item.product_variant,
                        quantity=cart_item.quantity,
                        unit_price=cart_item.product_variant.price
                    ))

                    cart_item.product_variant.stock -= cart_item.quantity
                    cart_item.product_variant.save()

                OrderItem.objects.bulk_create(order_items)

                cart_items.delete()

                return CreateOrderMutation(
                    success=True,
                    message="Order created successfully",
                    order=order
                )

        except Cart.DoesNotExist:
            return CreateOrderMutation(
                success=False,
                message="Cart not found"
            )
        except Address.DoesNotExist:
            return CreateOrderMutation(
                success=False,
                message="Address not found"
            )
        except Exception as e:
            return CreateOrderMutation(
                success=False,
                message=str(e)
            )

class UpdateOrderMutation(graphene.Mutation):
    order = graphene.Field(OrderNode)
    class Arguments:
        order = graphene.ID(required=True)
        status = graphene.String(required=False)
        shipping_address = graphene.ID(required=False)
        billing_address = graphene.ID(required=False)

    def mutate(self,info,order,status=None,shipping_address=None,billing_address=None):
        try:
            order = Order.objects.get(id=order)
            if status:
                order.status=status
            if shipping_address:
                shipping_address = Address.objects.get(id=shipping_address)
                order.shipping_address=shipping_address
            if billing_address:
                billing_address = Address.objects.get(id=billing_address)
                order.billing_address=billing_address
            return UpdateOrderMutation(order=order)
        except Exception as e:
            raise Exception(str(e))

class CreateReviewMutation(graphene.Mutation):
    review = graphene.Field(ReviewType)
    class Arguments:
        rating = graphene.Int(required=True)
        comment = graphene.String(required=True)
        product = graphene.ID(required=True)

    def mutate(self,info,rating,comment,product):
        user = info.context.user
        if user.is_anonymous:
            raise Exception('Lütfen giriş yapınız.')
        try:
            product = Products.objects.get(id=product)
            review = Review(
                user=user,
                product=product,
                comment=comment,
                rating=rating,
            )
            review.save()
            return CreateReviewMutation(review=review)
        except Exception as e:
            raise Exception(str(e))


#-----------------------------------------------------------------------------------------------
class Query(graphene.ObjectType):
    product_variant = relay.Node.Field(ProductVariantNode)
    all_product_variants = DjangoFilterConnectionField(ProductVariantNode)
    products = relay.Node.Field(ProductNode)
    all_products = DjangoFilterConnectionField(ProductNode)
    order = relay.Node.Field(OrderNode)
    category = relay.Node.Field(CategoryNode)


class Mutation(graphene.ObjectType):
    create_product_variant = CreateProductVariantMutation.Field()
    update_product_variant = UpdateProductVariantMutation.Field()
    delete_product_variant = DeleteProductVariantMuttion.Field()

    create_product = CreateProductMutation.Field()
    update_product = UpdateProductMutation.Field()
    delete_product = DeleteProductMutation.Field()

    create_category = CreateCategoryMutation.Field()
    update_category = UpdateCategoryMutation.Field()
    delete_category = DeleteCategoryMutation.Field()

    create_variant_option = CreateVariantOptionMutation.Field()
    update_variant_option = UpdateVariantOptionMutation.Field()
    delete_variant_option = DeleteVariantOptionMutation.Field()

    create_variant_value = CreateVariantValueMutation.Field()
    update_variant_value = UpdateVariantValueMutation.Field()
    delete_variant_value = DeleteVariantValueMutation.Field()

    create_variant = CreateVariantMutation.Field()
    update_variant = UpdateVariantMutation.Field()
    delete_variant = DeleteVariantMutation.Field()

    create_address = CreateAddressMutation.Field()
    update_address = UpdateAddressMutation.Field()
    delete_address = DeleteAddressMutation.Field()

    add_to_cart = AddToCartMutation.Field()
    update_cart_item = UpdateCartItemMutation.Field()

    create_order = CreateOrderMutation.Field()
    update_order = UpdateOrderMutation.Field()

    create_review = CreateReviewMutation.Field()