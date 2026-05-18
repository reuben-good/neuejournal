from django.contrib import admin

from .models import Sticker, StickerPack


# Register your models here.
class StickerInline(admin.TabularInline):
    model = Sticker
    extra = 1


@admin.register(StickerPack)
class StickerPackAdmin(admin.ModelAdmin):
    list_display = ["name", "artist"]
    inlines = [StickerInline]
