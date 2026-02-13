import json
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.db.models import Sum, Prefetch
from django.utils import timezone
from django.http import JsonResponse
from django.contrib import messages

# Seus models e forms
from .models import Produto, Pedido, ItemPedido, Configuracao, Categoria
from .forms import ProdutoForm

# =============================================================================
# 1. AUTENTICAÇÃO
# =============================================================================

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')


# =============================================================================
# 2. GESTÃO (DASHBOARD)
# =============================================================================

@login_required
def dashboard_gestor(request):
    config = Configuracao.objects.filter(id=1).first()
    
    # Lógica Financeira (Faturamento)
    hoje = timezone.now()
    inicio_dia = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def calcular_faturamento(data_inicio):
        return Pedido.objects.filter(
            data_criacao__gte=data_inicio, 
            finalizado=True
        ).aggregate(total=Sum('valor_total'))['total'] or 0

    # Top 5 Produtos (Para o gráfico)
    top_produtos_raw = ItemPedido.objects.filter(pedido__finalizado=True)\
        .values('produto__nome')\
        .annotate(total_vendido=Sum('quantidade'))\
        .order_by('-total_vendido')[:5]

    # Preparação dos dados do Gráfico
    chart_labels = [] 
    for i in range(6, -1, -1):
        data = hoje - timedelta(days=i)
        chart_labels.append(data.strftime("%d/%m"))

    chart_datasets = []
    cores = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

    for index, item in enumerate(top_produtos_raw):
        nome_prod = item['produto__nome']
        vendas_dia_a_dia = []
        for i in range(6, -1, -1):
            inicio_janela = (hoje - timedelta(days=i)).replace(hour=0, minute=0, second=0)
            fim_janela = (hoje - timedelta(days=i)).replace(hour=23, minute=59, second=59)
            
            qtd = ItemPedido.objects.filter(
                produto__nome=nome_prod,
                pedido__finalizado=True,
                pedido__data_criacao__range=(inicio_janela, fim_janela)
            ).aggregate(s=Sum('quantidade'))['s'] or 0
            vendas_dia_a_dia.append(qtd)
        
        chart_datasets.append({
            'label': nome_prod,
            'data': vendas_dia_a_dia,
            'borderColor': cores[index % len(cores)],
            'backgroundColor': cores[index % len(cores)],
            'tension': 0.4,
            'fill': False
        })

    context = {
        'faturamento_diario': calcular_faturamento(inicio_dia),
        'faturamento_semanal': calcular_faturamento(hoje - timedelta(days=7)),
        'faturamento_mensal': calcular_faturamento(hoje.replace(day=1)),
        'config': config,
        'meta_diaria': config.meta_diaria if config else 1000.00,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_datasets_json': json.dumps(chart_datasets),
    }
    
    return render(request, 'gestao/dashboard.html', context)


# =============================================================================
# 3. PRODUTOS E CADASTROS
# =============================================================================

@login_required
def produtos_view(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('produtos')
    else:
        form = ProdutoForm()

    lista_produtos = Produto.objects.all().order_by('nome')

    context = {
        'form': form,
        'lista_produtos': lista_produtos,
        'total_produtos': lista_produtos.count()
    }
    return render(request, 'gestao/produtos.html', context)

@login_required
def editar_produto(request, id):
    produto = get_object_or_404(Produto, id=id)
    
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto)
        if form.is_valid():
            form.save()
            # Redireciona para a lista de produtos após editar
            return redirect('produtos') 
    else:
        form = ProdutoForm(instance=produto)
        
    return render(request, 'gestao/editar_produto.html', {'form': form, 'produto': produto})


# =============================================================================
# 4. CONFIGURAÇÕES E PERFIL
# =============================================================================

@login_required
def atualizar_config(request):
    if request.method == 'POST':
        config, created = Configuracao.objects.get_or_create(id=1)
        config.nome_empresa = request.POST.get('nome_empresa')
        config.horario_abertura = request.POST.get('horario_abertura')
        config.horario_fechamento = request.POST.get('horario_fechamento')
        
        dias = ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo']
        for dia in dias:
            setattr(config, dia, dia in request.POST)
            
        if request.POST.get('meta_diaria'):
            config.meta_diaria = request.POST.get('meta_diaria').replace(',', '.')
            
        if request.FILES.get('foto_capa'):
            config.foto_capa = request.FILES['foto_capa']
            
        config.save()
    return redirect('dashboard')

@login_required
def perfil_view(request):
    config = Configuracao.objects.filter(id=1).first()
    total_faturamento = Pedido.objects.filter(finalizado=True).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    total_pedidos = Pedido.objects.filter(finalizado=True).count()
    
    context = {
        'config': config,
        'total_faturamento': total_faturamento,
        'total_pedidos': total_pedidos,
        'visualizacoes': config.visualizacoes_cardapio if config else 0
    }
    return render(request, 'core/perfil.html', context)


# =============================================================================
# 5. VISÃO PÚBLICA (CARDÁPIO)
# =============================================================================

def cardapio_view(request):
    config = Configuracao.objects.filter(id=1).first()
    if config:
        config.visualizacoes_cardapio += 1
        config.save()
    
    # Exibe apenas categorias que possuem produtos ATIVOS
    categorias = Categoria.objects.filter(produtos__ativo=True).distinct().prefetch_related(
        Prefetch('produtos', queryset=Produto.objects.filter(ativo=True))
    )

    if config:
        abertura = config.horario_abertura.strftime('%H:%M')
        fechamento = config.horario_fechamento.strftime('%H:%M')
        horario_texto = f"Aberto das {abertura} às {fechamento}"
    else:
        horario_texto = "Horário não configurado"

    context = {
        'nome_empresa': config.nome_empresa if config else "SID Burguer & Co.",
        'horario_funcionamento': horario_texto,
        'foto_capa': config.foto_capa.url if config and config.foto_capa else "https://images.unsplash.com/photo-1550547660-d9450f859349?q=80&w=1000",
        'categorias': categorias,
    }
    return render(request, 'core/cardapio.html', context)


# =============================================================================
# 6. LÓGICA DO CARRINHO
# =============================================================================

def _get_carrinho(request):
    """Função auxiliar para pegar ou criar o carrinho da sessão atual"""
    if not request.session.session_key:
        request.session.create()
    session_id = request.session.session_key
    
    # Busca um pedido em aberto (finalizado=False) para essa sessão
    pedido, created = Pedido.objects.get_or_create(
        sessao_id=session_id, 
        finalizado=False,
        defaults={'valor_total': 0}
    )
    return pedido

def ver_carrinho(request):
    pedido = _get_carrinho(request)
    itens = pedido.itens.all().select_related('produto')
    
    # Recalcula o total na hora de exibir para garantir precisão
    total = sum(item.produto.preco * item.quantidade for item in itens)
    pedido.valor_total = total
    pedido.save()

    return render(request, 'core/carrinho.html', {
        'pedido': pedido, 
        'itens': itens,
        'total': total
    })

def remover_item_carrinho(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(ItemPedido, id=item_id)
        # Segurança: garante que o item pertence ao carrinho da sessão atual
        if item.pedido.sessao_id == request.session.session_key:
            item.delete()
            messages.success(request, 'Item removido do carrinho.')
    return redirect('ver_carrinho')

# core/views.py

def finalizar_pedido(request):
    if request.method == 'POST':
        pedido = _get_carrinho(request)
        if pedido.itens.count() == 0:
            messages.error(request, 'Seu carrinho está vazio.')
            return redirect('ver_carrinho')
        
        # Captura os dados do formulário de entrega
        pedido.nome_cliente = request.POST.get('nome_cliente')
        pedido.telefone = request.POST.get('telefone')
        pedido.endereco = request.POST.get('endereco')
        pedido.forma_pagamento = request.POST.get('forma_pagamento')
        
        # Opcional: Se for dinheiro, pode pegar o troco aqui também

        pedido.finalizado = True
        pedido.save()
        
        request.session.flush() 
        
        return render(request, 'core/sucesso.html', {'pedido': pedido})
    
    return redirect('ver_carrinho')


# =============================================================================
# 7. APIs (JSON) - Ajax e Fetch
# =============================================================================

@login_required
@require_POST
def api_criar_categoria(request):
    try:
        dados = json.loads(request.body)
        nome_categoria = dados.get('nome')

        if not nome_categoria:
            return JsonResponse({'sucesso': False, 'erro': 'O nome da categoria não pode estar vazio.'})

        if Categoria.objects.filter(nome__iexact=nome_categoria).exists():
            return JsonResponse({'sucesso': False, 'erro': 'Esta categoria já existe.'})

        nova_cat = Categoria.objects.create(nome=nome_categoria)

        return JsonResponse({
            'sucesso': True,
            'id': nova_cat.id,
            'nome': nova_cat.nome
        })

    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})

@login_required
def api_excluir_categoria(request, id):
    if request.method == 'POST':
        try:
            categoria = Categoria.objects.get(id=id)
            if categoria.produtos.exists():
                return JsonResponse({
                    'status': 'erro', 
                    'mensagem': f'Não é possível excluir "{categoria.nome}" pois existem produtos vinculados a ela.'
                })
            categoria.delete()
            return JsonResponse({'status': 'sucesso'})
        except Categoria.DoesNotExist:
            return JsonResponse({'status': 'erro', 'mensagem': 'Categoria não encontrada.'}, status=404)
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido'}, status=405)

@login_required
def api_alternar_status(request, id):
    if request.method == 'POST':
        try:
            produto = Produto.objects.get(id=id)
            produto.ativo = not produto.ativo
            produto.save()
            return JsonResponse({'status': 'sucesso', 'ativo': produto.ativo})
        except Produto.DoesNotExist:
            return JsonResponse({'status': 'erro', 'mensagem': 'Produto não encontrado'}, status=404)
    return JsonResponse({'status': 'erro', 'mensagem': 'Método não permitido'}, status=405)

# Compatibilidade para urls antigas (se houver)
@login_required
def alternar_status_produto(request, id):
    return api_alternar_status(request, id)

@require_POST
def adicionar_item_api(request, produto_id):
    # 1. Busca o carrinho (sessão)
    pedido = _get_carrinho(request)
    
    # 2. Busca o produto
    produto = get_object_or_404(Produto, id=produto_id)
    
    # 3. Busca o item no carrinho ou cria um novo
    # (Note que usamos 'defaults' para definir o preço caso seja criado agora)
    item, created = ItemPedido.objects.get_or_create(
        pedido=pedido,
        produto=produto,
        defaults={'preco': produto.preco, 'quantidade': 0}
    )
    
    # 4. Incrementa a quantidade
    item.quantidade += 1
    item.save()
    
    # 5. Atualiza os totais do pedido
    itens = pedido.itens.all()
    # Soma (Preço * Quantidade) de todos os itens
    valor_total = sum(i.produto.preco * i.quantidade for i in itens)
    
    pedido.valor_total = valor_total
    pedido.save()

    # 6. RETORNO OBRIGATÓRIO (Isso estava faltando ou mal posicionado)
    return JsonResponse({
        'status': 'sucesso', 
        'qtd_total': itens.aggregate(Sum('quantidade'))['quantidade__sum'] or 0,
        'valor_total': valor_total
    })


def limpar_carrinho(request):
    if request.method == 'POST':
        pedido = _get_carrinho(request)
        pedido.delete() # Remove o pedido e todos os itens vinculados
        messages.success(request, 'Carrinho esvaziado com sucesso.')
    return redirect('cardapio')


# core/views.py

def finalizar_pedido(request):
    if request.method == 'POST':
        pedido = _get_carrinho(request)
        if pedido.itens.count() == 0:
            return redirect('ver_carrinho')
        
        pedido.nome_cliente = request.POST.get('nome_cliente')
        pedido.telefone = request.POST.get('telefone')
        
        # Captura os campos divididos
        pedido.rua = request.POST.get('rua')
        pedido.bairro = request.POST.get('bairro')
        pedido.numero = request.POST.get('numero')
        
        pedido.forma_pagamento = request.POST.get('forma_pagamento')
        pedido.finalizado = True
        pedido.save()
        
        request.session.flush() 
        return render(request, 'core/sucesso.html', {'pedido': pedido})
    return redirect('ver_carrinho')