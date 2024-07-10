from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

class CustomUserAdmin(UserAdmin):
    model = Usuario
    list_display = ('email', 'nombre', 'is_admin', 'is_director', 'is_profesor', 'is_active')
    list_filter = ('is_admin', 'is_director', 'is_profesor', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('nombre', 'codigo')}),
        ('Permissions', {'fields': ('is_admin', 'is_director', 'is_profesor', 'is_active')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombre', 'codigo', 'password1', 'password2', 'is_admin', 'is_director', 'is_profesor', 'is_active'),
        }),
    )
    search_fields = ('email', 'nombre', 'codigo')
    ordering = ('email',)

admin.site.register(Usuario, CustomUserAdmin)

# Register your models here.
