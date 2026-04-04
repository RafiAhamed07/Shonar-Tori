from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html

from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Store profile"
    fk_name = "user"
    fields = ("is_email_verified", "email_token", "profile_image")


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active", "date_joined")
    ordering = ("-date_joined",)

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            return []
        if not Profile.objects.filter(user=obj).exists():
            return []
        return super().get_inline_instances(request, obj)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user_email",
        "user_name_display",
        "is_email_verified",
        "has_image",
        "updated_at",
    ]
    list_filter = ["is_email_verified", "updated_at"]
    search_fields = [
        "user__email",
        "user__username",
        "user__first_name",
        "user__last_name",
    ]
    ordering = ["-updated_at"]
    list_select_related = ["user"]
    readonly_fields = ["uid", "user", "created_at", "updated_at", "profile_preview"]
    raw_id_fields = ["user"]

    fieldsets = (
        (None, {"fields": ("user", "is_email_verified", "email_token")}),
        ("Image", {"fields": ("profile_image", "profile_preview")}),
        ("System", {"fields": ("uid", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Email", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Name")
    def user_name_display(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description="Photo", boolean=True)
    def has_image(self, obj):
        return bool(obj.profile_image)

    @admin.display(description="Preview")
    def profile_preview(self, obj):
        if obj.pk and obj.profile_image:
            return format_html(
                '<img src="{}" width="120" style="border-radius:8px;object-fit:cover;" />',
                obj.profile_image.url,
            )
        return "—"
