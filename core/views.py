from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.db.models import Sum, Prefetch
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
import json

from .models import Produto, Pedido, ItemPedido, Configuracao, Categoria
from .forms import ProdutoForm

# --- 1. AUTENTICAÇÃO ---

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


# --- 2. GESTÃO (DASHBOARD) ---

@login_required
def dashboard_gestor(request):
    config = Configuracao.objects.filter(id=1).first()

    # REMOVIDO: Lógica de cadastro de produtos (movido para produtos_view)
    
    # Lógica Financeira (Faturamento)
    hoje = timezone.now()
    inicio_dia = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def calcular_faturamento(data_inicio):
        return Pedido.objects.filter(
            data_criacao__gte=data_inicio, 
            finalizado=True
        ).aggregate(total=Sum('valor_total'))['total'] or 0

    # Top 5 Produtos (Mantido para o gráfico)
    top_produtos_raw = ItemPedido.objects.filter(pedido__finalizado=True)\
        .values('produto__nome')\
        .annotate(total_vendido=Sum('quantidade'))\
        .order_by('-total_vendido')[:5]

    # Preparação Gráfico
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
        # REMOVIDO: lista_produtos e form
    }
    
    return render(request, 'gestao/dashboard.html', context)


# --- NOVA VIEW: PÁGINA DE PRODUTOS ---

@login_required
def produtos_view(request):
    # Lógica de Cadastro (Movida para cá)
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('produtos') # Redireciona para a mesma página limpa
    else:
        form = ProdutoForm()

    # Lista completa para a tabela
    lista_produtos = Produto.objects.all().order_by('nome')

    context = {
        'form': form,
        'lista_produtos': lista_produtos,
        'total_produtos': lista_produtos.count()
    }
    return render(request, 'gestao/produtos.html', context)


# --- 3. CONFIGURAÇÕES E API ---

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

# API (JSON) para o botão Switch funcionar sem recarregar
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

# Função antiga (Compatibilidade para não quebrar urls.py se ainda estiver lá)
@login_required
def alternar_status_produto(request, id):
    return api_alternar_status(request, id) # Redireciona para a lógica da API ou Dashboard


# --- 4. CARDÁPIO E EDIÇÃO ---

def cardapio_view(request):
    config = Configuracao.objects.filter(id=1).first()
    if config:
        config.visualizacoes_cardapio += 1
        config.save()

    
    # Cliente vê APENAS produtos ativos
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

@login_required
def editar_produto(request, id):
    produto = get_object_or_404(Produto, id=id)
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = ProdutoForm(instance=produto)
    return render(request, 'gestao/editar_produto.html', {'form': form, 'produto': produto})

# Em core/views.py

@login_required
def api_excluir_categoria(request, id):
    if request.method == 'POST':
        try:
            categoria = Categoria.objects.get(id=id)
            
            # Verificação de Segurança: A categoria tem produtos?
            if categoria.produtos.exists(): # 'produtos' é o related_name padrão ou produto_set
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
def perfil_view(request):
    config = Configuracao.objects.filter(id=1).first()
    
    # Estatísticas Gerais (Vitalício)
    total_faturamento = Pedido.objects.filter(finalizado=True).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    total_pedidos = Pedido.objects.filter(finalizado=True).count()
    
    context = {
        'config': config,
        'total_faturamento': total_faturamento,
        'total_pedidos': total_pedidos,
        'visualizacoes': config.visualizacoes_cardapio if config else 0
    }
    return render(request, 'core/perfil.html', context)