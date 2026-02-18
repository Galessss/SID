from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Perfil, Produto, Categoria, Insumo, Pedido, ItemPedido, Configuracao

# 1. Configurar o Perfil para aparecer dentro do Usuário
class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    verbose_name_plural = 'Perfil do Usuário'

# 2. Personalizar o Admin de Usuários
class CustomUserAdmin(UserAdmin):
    inlines = (PerfilInline, )
    list_display = ('username', 'email', 'first_name', 'get_tipo', 'is_active')
    list_filter = ('is_active', 'perfil__tipo_usuario')
    
    def get_tipo(self, instance):
        if hasattr(instance, 'perfil'):
            return instance.perfil.get_tipo_usuario_display()
        return "-"
    get_tipo.short_description = 'Tipo de Conta'

# 3. Re-registrar o UserAdmin com segurança
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, CustomUserAdmin)

# 4. Registrar os modelos do sistema (Usando decoradores para evitar duplicidade)

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'categoria', 'ativo')
    list_filter = ('categoria', 'ativo')
    search_fields = ('nome',)

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)

@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'quantidade_atual', 'unidade_medida', 'data_validade')
    list_filter = ('unidade_medida',)

@admin.register(Configuracao)
class ConfiguracaoAdmin(admin.ModelAdmin):
    list_display = ('nome_empresa', 'horario_abertura', 'horario_fechamento')

# Configuração para mostrar os itens dentro do Pedido no Admin
class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0 # Não mostra linhas vazias extras

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome_cliente', 'valor_total', 'solicitar_entrega', 'status_entrega', 'finalizado')
    list_filter = ('solicitar_entrega', 'status_entrega', 'finalizado')
    search_fields = ('nome_cliente', 'id')
    inlines = [ItemPedidoInline]