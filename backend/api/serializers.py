import base64

from django.core.files.base import ContentFile
from django.core.validators import MaxLengthValidator, RegexValidator
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404

from djoser.serializers import UserCreateSerializer, UserSerializer

from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.fields import IntegerField, SerializerMethodField
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer
from rest_framework.validators import UniqueValidator

from recipes.models import Ingredient, IngredientInRecipe, Recipe, Tag
from users.models import Subscribe, User

USERNAME_MAX_LENGTH = 150
TAG_MAX_LENGTH = 32
EMAIL_MAX_LENGTH = 254


class Base64ImageField(serializers.ImageField):
    """Поле для обработки изображений в формате base64."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(data)


class CustomUserSerializer(UserSerializer):
    """Просмотр информации о пользователе."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(allow_null=True)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Subscribe.objects.filter(
            user=request.user, author=obj
        ).exists()


class AvatarUserSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ['avatar']


class UserSerializer(UserCreateSerializer):
    """Регистрация нового пользователя."""

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(
        validators=[
            MaxLengthValidator(
                USERNAME_MAX_LENGTH,
                'Имя пользователя не должно быть длинее 150 символов'
            ),
            UniqueValidator(
                queryset=User.objects.all(),
                message='Это имя пользователя уже занято'
            ),
            RegexValidator(
                regex=r'^[\w.@+-]+',
                message='Имя пользователя содержит недопустимые символы',
            ),
        ]
    )
    email = serializers.EmailField(
        validators=[
            MaxLengthValidator(
                EMAIL_MAX_LENGTH,
                'Email не должен превышать 254 символа'
            ),
            RegexValidator(
                regex=r'^[\w.@+-]+',
                message=(
                    'Адрес электронной почты содержит '
                    'недопустимые символы'
                ),
            ),
        ]
    )
    first_name = serializers.CharField(
        validators=[
            MaxLengthValidator(
                USERNAME_MAX_LENGTH,
                'Имя не должно быть длинее 150 символов'
            ),
        ]
    )
    last_name = serializers.CharField(
        required=True,
        validators=[
            MaxLengthValidator(
                USERNAME_MAX_LENGTH,
                'Фамилия не должна быть длинее 150 символов'
            ),
        ]
    )

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email', 'password'
        )

    def validate(self, data):
        if 'last_name' not in data:
            raise serializers.ValidationError("Last name is required")
        return data


class SubscribeSerializer(CustomUserSerializer):
    """
    Сериализатор для подписки.
    """

    recipes_count = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + (
            'recipes_count', 'recipes',
        )
        read_only_fields = ('email', 'username',)

    def validate(self, data):
        """
        Валидация данных подписки.
        """

        author = self.instance
        user = self.context.get('request').user
        if Subscribe.objects.filter(author=author, user=user).exists():
            raise ValidationError(
                'Вы уже подписаны на этого пользователя!',
                code=status.HTTP_400_BAD_REQUEST
            )
        if user == author:
            raise ValidationError(
                'Вы не можете подписаться на самого себя!',
                code=status.HTTP_400_BAD_REQUEST
            )
        return data

    def get_recipes_count(self, obj):
        """
        Получение количества рецептов.
        """

        return obj.recipes.count()

    def get_recipes(self, obj):
        """
        Получение списка рецептов.
        """

        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[:int(limit)]
        serializer = RecipeShortSerializer(recipes, many=True, read_only=True)
        return serializer.data


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ингредиентов.
    """

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class TagSerializer(serializers.ModelSerializer):
    """
    Сериализатор для тегов.
    """

    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class RecipeReadSerializer(ModelSerializer):
    """
    Сериализатор для чтения рецептов.
    """

    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = SerializerMethodField()
    image = Base64ImageField()
    is_favorited = SerializerMethodField(read_only=True)
    is_in_shopping_cart = SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_ingredients(self, obj):
        """
        Получение ингредиентов рецепта.
        """

        ingredients = obj.ingredients.values(
            'id',
            'name',
            'measurement_unit',
            amount=F('ingredientinrecipe__amount')
        )
        return ingredients

    def get_is_favorited(self, obj):
        """
        Проверка, находится ли рецепт в избранном.
        """

        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.favorites.filter(recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        """
        Проверка, находится ли рецепт в корзине покупок.
        """

        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.shopping_cart.filter(recipe=obj).exists()

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        if tags is not None:
            # Обновите теги рецепта
            instance.tags.set(tags)
        return super().update(instance, validated_data)


class IngredientInRecipeWriteSerializer(ModelSerializer):
    """
    Сериализатор для записи ингредиентов в рецепте.
    """

    id = IntegerField(write_only=True)

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount')


class RecipeWriteSerializer(ModelSerializer):
    """
    Сериализатор для записи рецептов.
    """

    tags = PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = IngredientInRecipeWriteSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def validate_ingredients(self, value):
        """
        Валидация ингредиентов рецепта.
        """

        ingredients = value
        if not ingredients:
            raise ValidationError('Нужен хотя бы один ингредиент!')
        ingredients_list = []
        for item in ingredients:
            ingredient = get_object_or_404(Ingredient, id=item['id'])
            if ingredient in ingredients_list:
                raise ValidationError('Ингридиенты не могут повторяться!')
            if int(item['amount']) <= 0:
                raise ValidationError(
                    'Количество ингредиента должно быть больше 0!'
                )
            ingredients_list.append(ingredient)
        return value

    def validate_tags(self, value):
        """
        Валидация тегов рецепта.
        """

        tags = value
        if not tags:
            raise ValidationError('Нужно выбрать хотя бы один тег!')
        tags_list = []
        for tag in tags:
            if tag in tags_list:
                raise ValidationError('Теги должны быть уникальными!')
            tags_list.append(tag)
        return value

    def validate_cooking_time(self, value):
        """
        Валидация времени приготовления рецепта.
        """
        if value <= 0:
            raise ValidationError('Время приготовления должно быть больше нуля.')
        elif value > 600:
            raise ValidationError('Время приготовления должно быть меньше 600 минут.')
        return value

    @transaction.atomic
    def create_ingredients_amounts(self, ingredients, recipe):
        """
        Создание объектов IngredientInRecipe для рецепта.
        """

        IngredientInRecipe.objects.bulk_create(
            [IngredientInRecipe(
                ingredient=Ingredient.objects.get(id=ingredient['id']),
                recipe=recipe,
                amount=ingredient['amount']
            ) for ingredient in ingredients]
        )

    @transaction.atomic
    def create(self, validated_data):
        """
        Создание рецепта с тегами и ингредиентами.
        """

        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients_amounts(ingredients=ingredients, recipe=recipe)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Обновление рецепта с тегами и ингредиентами.
        """

        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)
        instance.tags.clear()
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_ingredients_amounts(
            ingredients=ingredients, recipe=instance
        )
        instance.save()
        return instance

    def to_representation(self, instance):
        """
        Преобразование объекта рецепта в его представление.
        """

        request = self.context.get('request')
        context = {'request': request}
        return RecipeReadSerializer(instance, context=context).data


class RecipeShortSerializer(ModelSerializer):
    """
    Сериализатор для краткого представления рецепта.
    """

    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Вывод короткой информации о рецепте."""

    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(CustomUserSerializer):
    """Получение подписок пользователя."""

    recipes = serializers.SerializerMethodField(read_only=True)
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        recipes = Recipe.objects.filter(author=obj)
        if limit:
            recipes = recipes[:int(limit)]
        serializer = ShortRecipeSerializer(recipes, many=True)
        return serializer.data

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        user = self.context['request'].user
        if not request or not user.is_authenticated:
            return False
        return obj.following.filter(user=user).exists()

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()
