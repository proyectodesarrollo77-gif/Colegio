"""Senales del modulo de usuarios: cache de permisos y preferencias."""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from config.permissions import invalidate_permission_cache

from .models import Role, RolePermission, User, UserModulePermission, UserPreference


@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    if created:
        UserPreference.objects.get_or_create(user=instance)
    invalidate_permission_cache(instance.pk)


@receiver([post_save, post_delete], sender=RolePermission)
def clear_role_permission_cache(sender, instance, **kwargs):
    invalidate_permission_cache()


@receiver([post_save, post_delete], sender=UserModulePermission)
def clear_user_permission_cache(sender, instance, **kwargs):
    invalidate_permission_cache(instance.user_id)


@receiver(post_save, sender=Role)
def clear_role_cache(sender, instance, **kwargs):
    invalidate_permission_cache()
