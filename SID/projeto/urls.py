from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    # --- AUTH ---
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # --- PAINEL ADMIN GERAL (Gestão de Usuários) ---
    path('admin-painel/', views.dashboard_admin, name='dashboard_admin'),
    path('admin-painel/criar/', views.admin_criar_usuario, name='admin_criar_usuario'),
    path('admin-painel/status/<int:user_id>/', views.admin_alternar_status, name='admin_alternar_status'),
    path('admin-painel/excluir/<int:user_id>/', views.admin_excluir_usuario, name='admin_excluir_usuario'),

    # --- DASHBOARD LOJISTA ---
    path('dashboard/', views.dashboard_gestor, name='dashboard'),
    path('dashboard/solicitar-entrega/<int:pedido_id>/', views.solicitar_entrega_loja, name='solicitar_entrega_loja'),
    path('atualizar-config/', views.atualizar_config, name='atualizar_config'),
    path('perfil/', views.perfil, name='perfil'),

    # --- PRODUTOS (CARDÁPIO) ---
    path('produtos/', views.produtos_view, name='produtos'),
    path('produtos/editar/<int:id>/', views.editar_produto, name='editar_produto'),
    path('produtos/deletar/<int:id>/', views.deletar_produto, name='deletar_produto'),

    # --- ESTOQUE (INSUMOS) ---
    # Nota: A rota antiga 'estoque_view' foi removida. Usamos apenas insumos agora.
    path('gestao/insumos/', views.estoque_insumos_view, name='estoque_insumos'),
    path('gestao/insumos/editar/<int:id>/', views.editar_insumo, name='editar_insumo'),
    path('gestao/insumos/deletar/<int:id>/', views.deletar_insumo, name='deletar_insumo'),

    # --- ÁREA DA ENTREGADORA ---
    path('entregas/', views.painel_entregas, name='painel_entregas'),
    path('entregas/status/<int:id>/<str:status>/', views.mudar_status_entrega, name='mudar_status_entrega'),
    path('api/entregas/', views.api_listar_entregas, name='api_listar_entregas'),
    path('entregas/recusar/<int:id>/', views.recusar_entrega, name='recusar_entrega'),


    # --- CLIENTE (CARDÁPIO & CARRINHO) ---
    path('cardapio/', views.cardapio_view, name='cardapio'),
    path('carrinho/', views.ver_carrinho, name='ver_carrinho'),
    path('carrinho/remover/<int:item_id>/', views.remover_item_carrinho, name='remover_item_carrinho'),
    path('carrinho/finalizar/', views.finalizar_pedido, name='finalizar_pedido'),
    path('carrinho/limpar/', views.limpar_carrinho, name='limpar_carrinho'),
    path('loja/<str:nome_empresa_slug>/', views.cardapio_publico, name='cardapio_publico'),

    # --- APIS (AJAX) ---
    path('api/criar-categoria/', views.api_criar_categoria, name='api_criar_categoria'),
    path('api/excluir-categoria/<int:id>/', views.api_excluir_categoria, name='api_excluir_categoria'),
    path('api/alternar-status/<int:id>/', views.api_alternar_status, name='api_alternar_status'),
    path('alternar-status/<int:id>/', views.alternar_status_produto, name='alternar_status'), # Legado
    path('api/carrinho/adicionar/<int:produto_id>/', views.adicionar_item_api, name='api_adicionar_item'),
    path('api/admin/usuarios/', views.api_listar_usuarios, name='api_listar_usuarios'),
    path('api/alternar-status-loja/', views.alternar_status_loja, name='alternar_status_loja'),

    # --- Pedidos ---
    path('pedido/<int:id>/status/', views.mudar_status_pedido, name='mudar_status_pedido'),



    #--- Entregas ---
    path('gestao/entregas/historico/', views.historico_entregas, name='historico_entregas'),
    path('entregas/equipe/', views.equipe_entregadores, name='equipe_entregadores'),
    path('entregas/equipe/excluir/<int:id>/', views.excluir_entregador, name='excluir_entregador'),




]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)