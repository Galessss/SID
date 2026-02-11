from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Produto, Pedido, ItemPedido

# Configuração bonita para o Admin
@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'categoria', 'ativo')
    list_filter = ('categoria', 'ativo')
    search_fields = ('nome',)

# Registrando os outros (opcional por enquanto)
admin.site.register(Pedido)
admin.site.register(ItemPedido)