import os
import django

# Установите настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodgram.settings')
django.setup()

from recipes.models import Ingredient, Tag

# Создание ингредиентов
Ingredient.objects.create(name='Ингредиент 1', measurement_unit='грамм')
Ingredient.objects.create(name='Ингредиент 2', measurement_unit='миллилитр')

# Создание тегов
Tag.objects.create(name='Тег 1', color='#FF0000', slug='tag1')
Tag.objects.create(name='Тег 2', color='#00FF00', slug='tag2')
Tag.objects.create(name='Тег 3', color='#0000FF', slug='tag3')

print("Ингредиенты и теги успешно созданы.")