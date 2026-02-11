from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

# Importações de Modelos e Forms locais
from .models import Produto, Pedido, ItemPedido, Configuracao
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
    # Cadastro de Produtos
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

    # Top 5 Produtos mais vendidos
    top_produtos = ItemPedido.objects.filter(pedido__finalizado=True)\
        .values('produto__nome')\
        .annotate(total_vendido=Sum('quantidade'))\
        .order_by('-total_vendido')[:5]

    context = {
        'form': form,
        'faturamento_diario': calcular_faturamento(inicio_dia),
        'faturamento_semanal': calcular_faturamento(inicio_semana),
        'faturamento_mensal': calcular_faturamento(inicio_mes),
        'top_produtos': top_produtos,
        'lista_produtos': Produto.objects.filter(ativo=True)
    }
    return render(request, 'gestao/dashboard.html', context)

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


# --- 3. CONFIGURAÇÕES DA PÁGINA ---

@login_required
def atualizar_config(request):
    """View para atualizar a imagem de capa e dados da empresa"""
    if request.method == 'POST' and request.FILES.get('foto_capa'):
        # Pega a config de ID 1 ou cria se não existir
        config, created = Configuracao.objects.get_or_create(id=1)
        config.foto_capa = request.FILES['foto_capa']
        config.save()
    return redirect('dashboard')


# --- 4. CARDÁPIO PÚBLICO ---

def cardapio_view(request):
    # Busca configurações (Capa, Nome, Horário)
    config = Configuracao.objects.filter(id=1).first()
    
    # Busca e agrupa produtos por categoria
    produtos_ativos = Produto.objects.filter(ativo=True)
    produtos_por_categoria = {}
    
    for produto in produtos_ativos:
        nome_categoria = produto.get_categoria_display()
        if nome_categoria not in produtos_por_categoria:
            produtos_por_categoria[nome_categoria] = []
        produtos_por_categoria[nome_categoria].append(produto)

    context = {
        'nome_empresa': config.nome_empresa if config else "SID Burguer & Co.",
        'horario_funcionamento': config.horario_info if config else "Aberto • Fecha às 23:00",
        'foto_capa': config.foto_capa.url if config and config.foto_capa else "https://images.unsplash.com/photo-1550547660-d9450f859349?q=80&w=1000",
        'cardapio': produtos_por_categoria
    }
    return render(request, 'core/cardapio.html', context)

@login_required
def atualizar_config(request):
    if request.method == 'POST':
        config, created = Configuracao.objects.get_or_create(id=1)
        
        config.nome_empresa = request.POST.get('nome_empresa')
        config.horario_abertura = request.POST.get('horario_abertura')
        config.horario_fechamento = request.POST.get('horario_fechamento')
        
        # Atualiza os dias (se o checkbox não for marcado, ele não vem no POST, por isso o 'get' com default False)
        config.segunda = 'segunda' in request.POST
        config.terca = 'terca' in request.POST
        config.quarta = 'quarta' in request.POST
        config.quinta = 'quinta' in request.POST
        config.sexta = 'sexta' in request.POST
        config.sabado = 'sabado' in request.POST
        config.domingo = 'domingo' in request.POST

        if request.FILES.get('foto_capa'):
            config.foto_capa = request.FILES['foto_capa']
            
        config.save()
        
    return redirect('dashboard')

def cardapio_view(request):
    # Busca a configuração (id=1)
    config = Configuracao.objects.filter(id=1).first()
    
    # Busca produtos ativos e agrupa por categoria
    produtos_ativos = Produto.objects.filter(ativo=True)
    produtos_por_categoria = {}
    
    for produto in produtos_ativos:
        nome_categoria = produto.get_categoria_display()
        if nome_categoria not in produtos_por_categoria:
            produtos_por_categoria[nome_categoria] = []
        produtos_por_categoria[nome_categoria].append(produto)

    # --- NOVO: Monta o texto de horário dinamicamente ---
    if config:
        # Formata as horas para exibir apenas HH:MM
        abertura = config.horario_abertura.strftime('%H:%M')
        fechamento = config.horario_fechamento.strftime('%H:%M')
        horario_texto = f"Aberto das {abertura} às {fechamento}"
    else:
        horario_texto = "Horário não configurado"

    context = {
        'nome_empresa': config.nome_empresa if config else "SID Burguer & Co.",
        'horario_funcionamento': horario_texto, # Agora usa a variável tratada acima
        'foto_capa': config.foto_capa.url if config and config.foto_capa else "https://images.unsplash.com/photo-1550547660-d9450f859349?q=80&w=1000",
        'cardapio': produtos_por_categoria
    }
    
    return render(request, 'core/cardapio.html', context)