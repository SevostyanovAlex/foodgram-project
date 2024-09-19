from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import exceptions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from djoser.serializers import SetPasswordSerializer

from api.pagination import LimitPageNumberPaginator
from api.serializers import (
    AvatarUserSerializer,
    CustomUserSerializer,
    SubscriptionSerializer,
    UserSerializer
)
from .models import Subscribe

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """Работа с пользователями."""

    queryset = User.objects.all()
    pagination_class = LimitPageNumberPaginator
    http_method_names = ['get', 'post', 'delete', 'put']

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve', 'user_self_profile'):
            return CustomUserSerializer
        elif self.action == 'user_avatar':
            return AvatarUserSerializer
        elif self.action == 'set_password':
            return SetPasswordSerializer
        return UserSerializer

    @action(
        detail=False, url_path='me',
        permission_classes=[IsAuthenticated],
        serializer_class=CustomUserSerializer
    )
    def user_self_profile(self, request):
        """Просмотр информации о пользователе."""
        user = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(
        methods=['put', 'delete'], detail=False, url_path='me/avatar',
        permission_classes=[IsAuthenticated],
        serializer_class=AvatarUserSerializer
    )
    def user_avatar(self, request):
        """Загрузка и удаление аватара пользователя."""
        user = self.request.user
        if request.method == 'PUT':
            serializer = self.get_serializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        if request.method == 'DELETE':
            user.avatar.delete()
            user.save()
            return Response(
                'Аватар удален.', status=status.HTTP_204_NO_CONTENT
            )
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=['post', 'delete'],
            serializer_class=SubscriptionSerializer)
    def subscribe(self, request, pk=None):
        """Подписка на пользователей."""
        user = self.request.user
        if not user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        author = get_object_or_404(User, pk=pk)
        if request.method == 'POST':
            if user == author:
                raise exceptions.ValidationError(
                    'Нельзя подписаться на самого себя.'
                )
            if Subscribe.objects.filter(
                user=user,
                author=author
            ).exists():
                raise exceptions.ValidationError(
                    'Вы уже подписаны на этого автора.'
                )
            Subscribe.objects.create(user=user, author=author)
            serializer = self.get_serializer(author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            if not Subscribe.objects.filter(
                user=user,
                author=author
            ).exists():
                raise exceptions.ValidationError(
                    'Подписка не была оформлена, либо удалена.'
                )
            subscription = get_object_or_404(
                Subscribe,
                user=user,
                author=author
            )
            subscription.delete()
            return Response(
                'Вы успешно отписались.', status=status.HTTP_204_NO_CONTENT
            )
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False, serializer_class=SubscriptionSerializer,
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        """Просмотр подписок пользователя."""
        user = self.request.user
        subscriptions = user.follower.all().order_by('id')
        users_id = subscriptions.values_list('author_id', flat=True)
        users = User.objects.filter(id__in=users_id)
        paginated_queryset = self.paginate_queryset(users)
        serializer = self.serializer_class(
            paginated_queryset, context={'request': request},
            many=True
        )
        return self.get_paginated_response(serializer.data)

    @action(methods=['post'], detail=False,
            permission_classes=[IsAuthenticated])
    def set_password(self, request, *args, **kwargs):
        """Изменение пароля."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.request.user.set_password(serializer.data['new_password'])
        self.request.user.save()
        return Response(
            {'Пароль успешно изменен.'}, status=status.HTTP_204_NO_CONTENT
        )
