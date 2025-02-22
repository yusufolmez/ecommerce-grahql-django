from django.core.management.base import BaseCommand
from faker import Faker
import random
from ecommerce.models import Categorys, Products, ProductVariants, VariantOptions, VariantValues, Variants
from userManage.models import CustomUser

class Command(BaseCommand):
    help = 'Sahte veri oluşturur ve veritabanına kaydeder'

    def handle(self, *args, **kwargs):
        fake = Faker()

        users = []
        for _ in range(5):
            user = CustomUser.objects.create_user(
                username=fake.user_name(),
                email=fake.email(),
                password=fake.password()
            )
            users.append(user)

        categories = []
        for _ in range(10):
            category = Categorys.objects.create(
                category_name=fake.word(),
                slug=fake.slug(),
                parent_category=None
            )
            categories.append(category)

        products = []
        for _ in range(1000):
            product = Products.objects.create(
                product_name=fake.word(),
                sku=fake.uuid4(),
                product_category=random.choice(categories),
                short_description=fake.text(max_nb_chars=100),
                product_description=fake.text(),
                created_by=random.choice(users)
            )
            products.append(product)

            variant_option = VariantOptions.objects.create(options_name="Color")
            variant_value = VariantValues.objects.create(value="Blue")
            variant = Variants.objects.create(
                variant_options_id=variant_option,
                variant_values_id=variant_value
            )

            product_variant = ProductVariants.objects.create(
                product_id=product,
                price=random.uniform(20000, 50000),
                other_variants={"model": random.choice([2022, 2023, 2024])}
            )

            product_variant.variants_id.add(variant)

        self.stdout.write(self.style.SUCCESS('Sahte veriler başarıyla oluşturuldu.'))
