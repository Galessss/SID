from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
# ADICIONEI O 'logout' AQUI NA IMPORTAÇÃO
from django.contrib.auth import login, logout
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

# Importando do mesmo diretório (pasta core)
from .models import Produto, Pedido, ItemPedido
from .forms import ProdutoForm

# 1. VIEW DE LOGIN
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

# --- NOVA FUNÇÃO DE LOGOUT (Adicionei isso) ---
def logout_view(request):
    logout(request)
    return redirect('login')

# 2. VIEW DO DASHBOARD
@login_required
def dashboard_gestor(request):
    # Lógica de Cadastro de Produtos
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = ProdutoForm()

    # Lógica Financeira
    hoje = timezone.now()
    inicio_dia = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_semana = hoje - timedelta(days=7)
    inicio_mes = hoje.replace(day=1)

    def calcular_faturamento(data_inicio):
        return Pedido.objects.filter(
            data_criacao__gte=data_inicio, 
            finalizado=True
        ).aggregate(total=Sum('valor_total'))['total'] or 0

    faturamento_diario = calcular_faturamento(inicio_dia)
    faturamento_semanal = calcular_faturamento(inicio_semana)
    faturamento_mensal = calcular_faturamento(inicio_mes)

    # Top Produtos
    top_produtos = ItemPedido.objects.filter(pedido__finalizado=True)\
        .values('produto__nome')\
        .annotate(total_vendido=Sum('quantidade'))\
        .order_by('-total_vendido')[:5]

    context = {
        'form': form,
        'faturamento_diario': faturamento_diario,
        'faturamento_semanal': faturamento_semanal,
        'faturamento_mensal': faturamento_mensal,
        'top_produtos': top_produtos,
        'lista_produtos': Produto.objects.filter(ativo=True)
    }
    
    return render(request, 'gestao/dashboard.html', context)

# 3. VIEW DE EDITAR PRODUTO
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