import json
import datetime
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.db.models import Sum, Prefetch, Q
from django.utils import timezone
from django.http import JsonResponse
from django.contrib import messages
from django.utils.text import slugify

# Seus Models e Forms
from .models import Produto, Pedido, ItemPedido, Configuracao, Categoria, Insumo, Perfil
from .forms import ProdutoForm, InsumoForm, NovoUsuarioForm, ConfiguracaoForm

# =============================================================================
# 1. AUTENTICAÇÃO E LOGIN
# =============================================================================

def login_view(request):
    if request.user.is_authenticated:
        # Redirecionamento para quem já está logado
        perfil = getattr(request.user, 'perfil', None)
        if request.user.is_superuser or (perfil and perfil.tipo_usuario == 'ADMIN'):
            return redirect('dashboard_admin')
        if perfil and perfil.tipo_usuario == 'ENTREGADORA':
            return redirect('painel_entregas')
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Garante que o perfil existe (caso o banco não o tenha criado)
                perfil, created = Perfil.objects.get_or_create(user=user)
                
                # Lógica de Redirecionamento por Tipo de Usuário
                if user.is_superuser or perfil.tipo_usuario == 'ADMIN':
                    return redirect('dashboard_admin')
                elif perfil.tipo_usuario == 'ENTREGADORA':
                    return redirect('painel_entregas')
                else:
                    return redirect('dashboard')
            else:
                messages.error(request, "Usuário ou senha inválidos.")
    else:
        form = AuthenticationForm()

    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')


# =============================================================================
# 2. PAINEL DO ADMINISTRADOR (GERAL)
# =============================================================================

@login_required
def dashboard_admin(request):
    # SEGURANÇA: Só deixa entrar se for ADMIN ou Superusuário
    if not request.user.is_superuser and request.user.perfil.tipo_usuario != 'ADMIN':
        messages.error(request, "Acesso restrito ao Administrador.")
        return redirect('dashboard')

    query = request.GET.get('q')
    usuarios = User.objects.all().exclude(id=request.user.id).select_related('perfil').order_by('-date_joined')

    if query:
        usuarios = usuarios.filter(
            Q(id__icontains=query) | 
            Q(username__icontains=query) | 
            Q(first_name__icontains=query)
        )

    config_geral = Configuracao.objects.filter(id=1).first()
    form = NovoUsuarioForm()

    return render(request, 'gestao/dashboard_admin.html', {
        'usuarios': usuarios, 
        'form': form, 
        'config_geral': config_geral
    })

@login_required
def admin_criar_usuario(request):
    if request.method == 'POST':
        form = NovoUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Se precisar mudar o tipo para ENTREGADORA logo na criação:
            tipo = request.POST.get('tipo_usuario')
            if tipo and hasattr(user, 'perfil'):
                user.perfil.tipo_usuario = tipo
                user.perfil.nome_empresa = user.first_name 
                user.perfil.save()
                
            messages.success(request, f'Usuário "{user.username}" criado com sucesso!')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erro: {error}")
            
    return redirect('dashboard_admin')

@login_required
def admin_alternar_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    status = "ativada" if user.is_active else "desativada"
    messages.success(request, f"Conta de {user.username} foi {status}.")
    return redirect('dashboard_admin')

@login_required
def admin_excluir_usuario(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, 'Usuário excluído permanentemente.')
    return redirect('dashboard_admin')

@login_required
def api_listar_usuarios(request):
    if not request.user.is_superuser and request.user.perfil.tipo_usuario != 'ADMIN':
        return JsonResponse({'erro': 'Não autorizado'}, status=403)

    usuarios = User.objects.all().exclude(id=request.user.id).select_related('perfil')
    config = Configuracao.objects.filter(id=1).first()
    
    data = []
    for u in usuarios:
        data.append({
            'id': u.id,
            'username': u.username,
            'empresa': u.first_name or "-",
            'tipo': u.perfil.get_tipo_usuario_display(),
            'tipo_raw': u.perfil.tipo_usuario,
            'is_active': u.is_active,
            'horario': f"{config.horario_abertura.strftime('%H:%M')} - {config.horario_fechamento.strftime('%H:%M')}" if config and hasattr(config, 'horario_abertura') and u.perfil.tipo_usuario == 'LOJISTA' else "N/A"
        })
    
    return JsonResponse({'usuarios': data})


# =============================================================================
# 3. GESTÃO LOJISTA (DASHBOARD)
# =============================================================================

@login_required
def dashboard_gestor(request):
    # 1. Bloqueia entregadores
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo_usuario == 'ENTREGADORA':
        return redirect('painel_entregas')

    # 2. Busca a configuração da loja logada
    config, created = Configuracao.objects.get_or_create(loja=request.user)
    
    # 3. Filtra os pedidos da loja que foram finalizados pelo cliente e NÃO FORAM CANCELADOS
    meus_pedidos_validos = Pedido.objects.filter(
        loja=request.user, 
        finalizado=True
    ).exclude(status_pedido='CANCELADO')
    
    hoje = timezone.localtime(timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # --- CÁLCULO DE VENDAS DINÂMICAS ---
    def calcular_faturamento(data_inicio):
        return meus_pedidos_validos.filter(
            data_criacao__gte=data_inicio
        ).aggregate(total=Sum('valor_total'))['total'] or 0

    faturamento_hoje = calcular_faturamento(hoje)
    faturamento_semanal = calcular_faturamento(hoje - timedelta(days=7))
    faturamento_mensal = calcular_faturamento(hoje.replace(day=1))
    
    faturamento_total = meus_pedidos_validos.aggregate(total=Sum('valor_total'))['total'] or 0
    total_pedidos = meus_pedidos_validos.count()
    visitas = config.visualizacoes_cardapio if config else 0
    
    meta = float(config.meta_diaria) if config and config.meta_diaria else 1000.0
    porcentagem_meta = (float(faturamento_hoje) / meta) * 100 if meta > 0 else 0
    progresso_barra = min(porcentagem_meta, 100)

    # --- LÓGICA DOS GRÁFICOS ---
    top_produtos_raw = ItemPedido.objects.filter(
        pedido__loja=request.user, 
        pedido__finalizado=True
    ).exclude(
        pedido__status_pedido='CANCELADO'
    ).values('produto__nome')\
     .annotate(total_vendido=Sum('quantidade'))\
     .order_by('-total_vendido')[:5]

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
            inicio_janela = (hoje - timedelta(days=i))
            fim_janela = inicio_janela.replace(hour=23, minute=59, second=59)
            
            qtd = ItemPedido.objects.filter(
                produto__nome=nome_prod,
                pedido__loja=request.user,
                pedido__finalizado=True,
                pedido__data_criacao__range=(inicio_janela, fim_janela)
            ).exclude(
                pedido__status_pedido='CANCELADO'
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
    
    ultimos_pedidos = Pedido.objects.filter(loja=request.user, finalizado=True).order_by('-data_criacao')[:15]

    context = {
        'faturamento_total': faturamento_total,
        'total_pedidos': total_pedidos,
        'visitas': visitas,
        'faturamento_hoje': faturamento_hoje,
        'faturamento_semanal': faturamento_semanal,
        'faturamento_mensal': faturamento_mensal,
        'meta': meta,
        'porcentagem_meta': round(porcentagem_meta, 1),
        'progresso_barra': progresso_barra,
        'config': config,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_datasets_json': json.dumps(chart_datasets),
        'ultimos_pedidos': ultimos_pedidos,
    }
    
    return render(request, 'gestao/dashboard.html', context)

# =============================================================================
# 4. PRODUTOS E CATEGORIAS
# =============================================================================

@login_required
def produtos_view(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            produto = form.save(commit=False)
            produto.loja = request.user
            produto.save()
            messages.success(request, "Produto cadastrado com sucesso!")
            return redirect('produtos')
    else:
        form = ProdutoForm(user=request.user)

    lista_produtos = Produto.objects.filter(loja=request.user).order_by('nome')
    total_produtos = lista_produtos.count()

    return render(request, 'gestao/produtos.html', {
        'form': form,
        'lista_produtos': lista_produtos,
        'total_produtos': total_produtos
    })

@login_required
def editar_produto(request, id):
    produto = get_object_or_404(Produto, id=id, loja=request.user)
    
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('produtos')
    else:
        form = ProdutoForm(instance=produto, user=request.user)
    
    return render(request, 'gestao/editar_produto.html', {
        'form': form, 
        'produto': produto
    })

@login_required
def deletar_produto(request, id):
    produto = get_object_or_404(Produto, id=id, loja=request.user)
    nome_produto = produto.nome
    produto.delete()
    messages.warning(request, f'Produto "{nome_produto}" removido permanentemente.')
    return redirect('produtos')


# =============================================================================
# 5. ESTOQUE DE INSUMOS
# =============================================================================

@login_required
def estoque_insumos_view(request):
    if request.method == 'POST':
        form = InsumoForm(request.POST)
        if form.is_valid():
            insumo = form.save(commit=False)
            insumo.loja = request.user
            insumo.save()
            messages.success(request, 'Insumo cadastrado com sucesso!')
            return redirect('estoque_insumos')
        else:
            messages.error(request, 'Erro ao cadastrar. Verifique os dados.')
    else:
        form = InsumoForm()

    insumos = Insumo.objects.filter(loja=request.user).order_by('data_validade')
    hoje = timezone.now().date()
    return render(request, 'gestao/estoque_insumos.html', {'insumos': insumos, 'form': form, 'hoje': hoje})

@login_required
def editar_insumo(request, id):
    insumo = get_object_or_404(Insumo, id=id, loja=request.user)
    if request.method == 'POST':
        form = InsumoForm(request.POST, instance=insumo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Insumo atualizado com sucesso!')
            return redirect('estoque_insumos')
    else:
        form = InsumoForm(instance=insumo)
    return render(request, 'gestao/editar_insumo.html', {'form': form, 'insumo': insumo})

@login_required
def deletar_insumo(request, id):
    insumo = get_object_or_404(Insumo, id=id, loja=request.user)
    insumo.delete()
    messages.success(request, 'Insumo removido com sucesso.')
    return redirect('estoque_insumos')


# =============================================================================
# 6. LOGÍSTICA E ENTREGAS
# =============================================================================

from django.db.models import Q
from django.utils import timezone

@login_required
def painel_entregas(request):
    # Proteção de acesso
    if request.user.perfil.tipo_usuario != 'ENTREGADORA' and not request.user.is_superuser:
        return redirect('dashboard')
        
    # 🌟 CORREÇÃO: Filtramos para mostrar apenas pedidos ativos e NÃO cancelados
    pedidos = Pedido.objects.filter(
        solicitar_entrega=True, 
        status_entrega__in=['AGUARDANDO', 'EM_ROTA']
    ).exclude(status_pedido='CANCELADO').select_related('loja', 'entregador_responsavel', 'loja__perfil').order_by('data_criacao')
    
    # Mantém a correção anterior: esconde o seu usuário (operador) da lista de motoboys
    entregadores = User.objects.filter(
        perfil__tipo_usuario='ENTREGADORA', 
        is_active=True
    ).exclude(id=request.user.id).order_by('first_name')
    
    return render(request, 'gestao/painel_entregas.html', {
        'pedidos': pedidos,
        'entregadores': entregadores
    })

@login_required
def mudar_status_entrega(request, id, status):
    pedido = get_object_or_404(Pedido, id=id)
    if status in ['EM_ROTA', 'ENTREGUE']:
        pedido.status_entrega = status
        
        if status == 'EM_ROTA':
            pedido.data_saida_entrega = timezone.now()
            
            # 🌟 GRAVA QUEM É O OPERADOR NO COMPUTADOR
            pedido.operador_despacho = request.user
            
            # GRAVA QUEM É O MOTOBOY SELECIONADO NA TELA
            if request.method == 'POST':
                entregador_id = request.POST.get('entregador_id')
                if entregador_id:
                    pedido.entregador_responsavel = get_object_or_404(User, id=entregador_id)
                else:
                    pedido.entregador_responsavel = request.user
            else:
                pedido.entregador_responsavel = request.user

        elif status == 'ENTREGUE':
            pedido.data_entregue = timezone.now()
            
        pedido.save()
        messages.success(request, f"Status atualizado para: {pedido.get_status_entrega_display()}")
        
    return redirect('painel_entregas')


@login_required
@require_POST
def recusar_entrega(request, id):
    pedido = get_object_or_404(Pedido, id=id)
    
    # Devolve o pedido para a loja apagando a solicitação de entrega
    pedido.solicitar_entrega = False
    pedido.status_entrega = None
    pedido.entregador_responsavel = None
    pedido.save()
    
    messages.warning(request, f"O Pedido #{pedido.id} foi recusado e devolvido à loja.")
    return redirect('painel_entregas')

@login_required
def solicitar_entrega_loja(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, loja=request.user)
    pedido.solicitar_entrega = True
    pedido.status_entrega = 'AGUARDANDO'
    pedido.save()
    messages.success(request, f"Entregador solicitado para o Pedido #{pedido.id}!")
    return redirect('dashboard')

from django.db.models import Q # Não esqueça de importar o Q no topo do arquivo!

@login_required
def historico_entregas(request):
    if request.user.perfil.tipo_usuario != 'ENTREGADORA' and not request.user.is_superuser:
        return redirect('dashboard')
        
    query = request.GET.get('q')
    pedidos = Pedido.objects.filter(status_entrega='ENTREGUE')

    # Sistema de busca multi-campo
    if query:
        pedidos = pedidos.filter(
            Q(id__icontains=query) | 
            Q(nome_cliente__icontains=query) |
            Q(bairro__icontains=query) |
            Q(loja__perfil__nome_empresa__icontains=query) |
            Q(entregador_responsavel__first_name__icontains=query) |
            Q(entregador_responsavel__username__icontains=query)
        )
    
    pedidos = pedidos.select_related('loja', 'operador_despacho', 'entregador_responsavel').order_by('-data_entregue')
    
    return render(request, 'gestao/historico_entregas.html', {'pedidos': pedidos, 'query': query})




# Adicione esta importação no topo do arquivo se ainda não tiver:
# from django.http import JsonResponse

@login_required
def api_listar_entregas(request):
    """
    API para buscar as entregas disponíveis ou em andamento.
    Retorna os dados em JSON para ser consumido via JavaScript.
    """
    # 1. Segurança: Apenas Entregadoras, Admins ou Superusers podem acessar
    perfil = getattr(request.user, 'perfil', None)
    if not request.user.is_superuser and (not perfil or perfil.tipo_usuario not in ['ENTREGADORA', 'ADMIN']):
        return JsonResponse({'erro': 'Acesso restrito a entregadores.'}, status=403)

    # 2. Busca os pedidos válidos (mesma lógica do painel_entregas)
    pedidos = Pedido.objects.filter(
        finalizado=True,
        solicitar_entrega=True
    ).exclude(
        status_entrega='ENTREGUE'
    ).exclude(
        status_pedido='CANCELADO'
    ).order_by('-data_criacao')

    # 3. Monta a lista de dicionários para transformar em JSON
    dados = []
    for p in pedidos:
        dados.append({
            'id': p.id,
            'nome_cliente': p.nome_cliente,
            'telefone': p.telefone,
            'rua': p.rua,
            'numero': p.numero,
            'bairro': p.bairro,
            'endereco_completo': f"{p.rua}, Nº {p.numero} - {p.bairro}",
            'status_entrega': p.status_entrega,
            'status_entrega_display': p.get_status_entrega_display(),
            'valor_total': float(p.valor_total),
            'data_criacao': p.data_criacao.strftime("%d/%m/%Y %H:%M"),
            'entregador_responsavel_id': p.entregador_responsavel.id if p.entregador_responsavel else None,
            'entregador_responsavel_nome': p.entregador_responsavel.username if p.entregador_responsavel else None,
        })

    return JsonResponse({'pedidos': dados})


# =============================================================================
# 7. CONFIGURAÇÕES E PERFIL
# =============================================================================

@login_required
def perfil(request):
    config, created = Configuracao.objects.get_or_create(loja=request.user)
    
    meus_pedidos_validos = Pedido.objects.filter(
        loja=request.user, 
        finalizado=True
    ).exclude(status_pedido='CANCELADO')
    
    total_faturamento = meus_pedidos_validos.aggregate(total=Sum('valor_total'))['total'] or 0
    total_pedidos = meus_pedidos_validos.count()

    context = {
        'config': config,
        'total_faturamento': total_faturamento,
        'total_pedidos': total_pedidos,
        'visualizacoes': config.visualizacoes_cardapio,
    }
    
    return render(request, 'core/perfil.html', context)

@login_required
@require_POST
def atualizar_config(request):
    config, created = Configuracao.objects.get_or_create(loja=request.user)
    
    novo_nome = request.POST.get('nome_empresa')
    config.nome_empresa = novo_nome
    config.loja_aberta = 'loja_aberta' in request.POST
    
    dias = ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo']
    for dia in dias:
        setattr(config, dia, dia in request.POST)
        
        abertura = request.POST.get(f'{dia}_abertura')
        fechamento = request.POST.get(f'{dia}_fechamento')
        setattr(config, f'{dia}_abertura', abertura if abertura else None)
        setattr(config, f'{dia}_fechamento', fechamento if fechamento else None)
        
    if request.POST.get('meta_diaria'):
        config.meta_diaria = request.POST.get('meta_diaria').replace(',', '.')
        
    if request.FILES.get('foto_capa'):
        config.foto_capa = request.FILES['foto_capa']
        
    config.save()

    if hasattr(request.user, 'perfil') and novo_nome:
        request.user.perfil.nome_empresa = novo_nome
        request.user.perfil.save()
        
    messages.success(request, 'Configurações atualizadas com sucesso!')
    return redirect('perfil')
# =============================================================================
# 8. VISÃO PÚBLICA (CARDÁPIO E CARRINHO)
# =============================================================================

@login_required
def cardapio_view(request):
    perfil = getattr(request.user, 'perfil', None)
    config = getattr(request.user, 'configuracao', None)
    
    nome_loja = None
    
    if perfil and perfil.nome_empresa:
        nome_loja = perfil.nome_empresa
    elif config and config.nome_empresa:
        nome_loja = config.nome_empresa
        
    if nome_loja:
        if perfil and not perfil.nome_empresa:
            try:
                perfil.nome_empresa = nome_loja
                perfil.save()
            except:
                pass 
                
        slug = slugify(nome_loja)
        return redirect('cardapio_publico', nome_empresa_slug=slug)
    
    messages.warning(request, "Por favor, preencha o Nome da Empresa nas configurações.")
    return redirect('dashboard')

def cardapio_publico(request, nome_empresa_slug):
    perfil = get_object_or_404(Perfil, nome_empresa__iexact=nome_empresa_slug.replace('-', ' '))
    loja_dona = perfil.user

    categorias = Categoria.objects.filter(loja=loja_dona).prefetch_related(
        Prefetch('produtos', queryset=Produto.objects.filter(loja=loja_dona, ativo=True), to_attr='produtos_da_loja')
    ).distinct()

    config = Configuracao.objects.filter(loja=loja_dona).first()

    agora = timezone.localtime(timezone.now())
    hora_atual = agora.time()
    dia_semana_index = agora.weekday()
    
    loja_aberta_agora = False
    motivo_fechado = "Fechado no momento."
    horario_texto = ""
    dias_semana = []
    foto_capa = ""

    if config:
        config.visualizacoes_cardapio += 1
        config.save()
        foto_capa = config.foto_capa.url if config.foto_capa else ""

        if hasattr(config, 'segunda_abertura'): 
            dias_semana = [
                {'nome': 'Seg', 'aberto': config.segunda, 'abre': config.segunda_abertura, 'fecha': config.segunda_fechamento},
                {'nome': 'Ter', 'aberto': config.terca, 'abre': config.terca_abertura, 'fecha': config.terca_fechamento},
                {'nome': 'Qua', 'aberto': config.quarta, 'abre': config.quarta_abertura, 'fecha': config.quarta_fechamento},
                {'nome': 'Qui', 'aberto': config.quinta, 'abre': config.quinta_abertura, 'fecha': config.quinta_fechamento},
                {'nome': 'Sex', 'aberto': config.sexta, 'abre': config.sexta_abertura, 'fecha': config.sexta_fechamento},
                {'nome': 'Sáb', 'aberto': config.sabado, 'abre': config.sabado_abertura, 'fecha': config.sabado_fechamento},
                {'nome': 'Dom', 'aberto': config.domingo, 'abre': config.domingo_abertura, 'fecha': config.domingo_fechamento},
            ]
            
            if config.loja_aberta:
                hoje_info = dias_semana[dia_semana_index]
                if not hoje_info['aberto']:
                    motivo_fechado = "Hoje não abrimos."
                else:
                    h_abre = hoje_info['abre']
                    h_fecha = hoje_info['fecha']
                    
                    if h_abre and h_fecha:
                        horario_texto = f"Aberto das {h_abre.strftime('%H:%M')} às {h_fecha.strftime('%H:%M')}"
                        if h_abre < h_fecha:
                            loja_aberta_agora = h_abre <= hora_atual <= h_fecha
                        else:
                            loja_aberta_agora = hora_atual >= h_abre or hora_atual <= h_fecha
                            
                        if not loja_aberta_agora:
                            motivo_fechado = f"Abrimos às {h_abre.strftime('%H:%M')}."
                    else:
                        loja_aberta_agora = True
                        horario_texto = "Aberto (Horário Flexível)"
            else:
                motivo_fechado = "Loja temporariamente fechada pelo gestor."

    context = {
        'nome_empresa': perfil.nome_empresa,
        'categorias': categorias,
        'config': config,
        'foto_capa': foto_capa,
        'horario_funcionamento': horario_texto,
        'dias_semana': dias_semana,
        'esta_aberto_hoje': loja_aberta_agora,
        'motivo_fechado': motivo_fechado,
    }
    return render(request, 'core/cardapio.html', context)


# =============================================================================
# 9. CARRINHO E PEDIDOS
# =============================================================================

def _get_carrinho(request):
    if not request.session.session_key:
        request.session.create()
    session_id = request.session.session_key
    pedido, created = Pedido.objects.get_or_create(sessao_id=session_id, finalizado=False, defaults={'valor_total': 0})
    return pedido

def ver_carrinho(request):
    pedido = _get_carrinho(request)
    itens = pedido.itens.all().select_related('produto')
    total = sum(item.produto.preco * item.quantidade for item in itens)
    pedido.valor_total = total
    pedido.save()
    return render(request, 'core/carrinho.html', {'pedido': pedido, 'itens': itens, 'total': total})

def remover_item_carrinho(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(ItemPedido, id=item_id)
        if item.pedido.sessao_id == request.session.session_key:
            item.delete()
            messages.success(request, 'Item removido.')
    return redirect('ver_carrinho')

def finalizar_pedido(request):
    if request.method == 'POST':
        pedido = _get_carrinho(request)
        if pedido.itens.count() == 0:
            messages.error(request, 'Carrinho vazio.')
            return redirect('ver_carrinho')
        
        pedido.nome_cliente = request.POST.get('nome_cliente')
        pedido.telefone = request.POST.get('telefone')
        pedido.rua = request.POST.get('rua')
        pedido.bairro = request.POST.get('bairro')
        pedido.numero = request.POST.get('numero')
        pedido.forma_pagamento = request.POST.get('forma_pagamento')
        
        pedido.finalizado = True
        pedido.save()
        
        messages.success(request, 'Pedido finalizado com sucesso! A loja já está preparando.')
        
        if pedido.loja and hasattr(pedido.loja, 'perfil') and pedido.loja.perfil.nome_empresa:
            slug = slugify(pedido.loja.perfil.nome_empresa)
            return redirect('cardapio_publico', nome_empresa_slug=slug)
        else:
            return redirect('cardapio')
            
    return redirect('ver_carrinho')

def limpar_carrinho(request):
    if request.method == 'POST':
        pedido = _get_carrinho(request)
        pedido.delete()
        messages.success(request, 'Carrinho esvaziado.')
        
    url_anterior = request.META.get('HTTP_REFERER', 'ver_carrinho')
    return redirect(url_anterior)

@login_required
@require_POST
def mudar_status_pedido(request, id):
    pedido = get_object_or_404(Pedido, id=id, loja=request.user)
    novo_status = request.POST.get('novo_status')
    
    if novo_status in ['PENDENTE', 'PREPARANDO', 'PRONTO', 'CANCELADO']:
        pedido.status_pedido = novo_status
        pedido.save()
        messages.success(request, f"O status do pedido #{pedido.id} foi atualizado para {pedido.get_status_pedido_display()}.")
    
    return redirect('dashboard')


# =============================================================================
# 10. APIS (AJAX)
# =============================================================================

@login_required
@require_POST
def api_criar_categoria(request):
    try:
        dados = json.loads(request.body)
        nome = dados.get('nome')
        if not nome: 
            return JsonResponse({'sucesso': False, 'erro': 'Nome vazio.'})
        
        if Categoria.objects.filter(nome__iexact=nome, loja=request.user).exists():
            return JsonResponse({'sucesso': False, 'erro': 'Você já tem essa categoria.'})
        
        nova_cat = Categoria.objects.create(nome=nome, loja=request.user)
        return JsonResponse({'sucesso': True, 'id': nova_cat.id, 'nome': nova_cat.nome})
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})

@login_required
def api_excluir_categoria(request, id):
    if request.method == 'POST':
        try:
            cat = Categoria.objects.get(id=id)
            if cat.produtos.exists():
                return JsonResponse({'status': 'erro', 'mensagem': 'Existem produtos nesta categoria.'})
            cat.delete()
            return JsonResponse({'status': 'sucesso'})
        except:
            return JsonResponse({'status': 'erro', 'mensagem': 'Erro ao excluir.'}, status=400)
    return JsonResponse({'status': 'erro'}, status=405)

@login_required
def api_alternar_status(request, id):
    if request.method == 'POST':
        try:
            prod = Produto.objects.get(id=id, loja=request.user)
            prod.ativo = not prod.ativo
            prod.save()
            return JsonResponse({'status': 'sucesso', 'ativo': prod.ativo})
        except:
            return JsonResponse({'status': 'erro'}, status=404)
    return JsonResponse({'status': 'erro'}, status=405)

@login_required
def alternar_status_produto(request, id):
    return api_alternar_status(request, id)

@require_POST
def adicionar_item_api(request, produto_id):
    pedido = _get_carrinho(request)
    produto = get_object_or_404(Produto, id=produto_id)
    
    if not pedido.loja:
        pedido.loja = produto.loja
        pedido.save()
        
    item, created = ItemPedido.objects.get_or_create(pedido=pedido, produto=produto, defaults={'preco': produto.preco, 'quantidade': 0})
    item.quantidade += 1
    item.save()
    
    valor_total = sum(i.produto.preco * i.quantidade for i in pedido.itens.all())
    pedido.valor_total = valor_total
    pedido.save()
    
    return JsonResponse({
        'status': 'sucesso', 
        'qtd_total': pedido.itens.aggregate(Sum('quantidade'))['quantidade__sum'] or 0,
        'valor_total': float(valor_total) 
    })

@login_required
@require_POST
def alternar_status_loja(request):
    config, created = Configuracao.objects.get_or_create(loja=request.user)
    config.loja_aberta = not config.loja_aberta
    config.save()
    return JsonResponse({'status': 'sucesso', 'aberta': config.loja_aberta})



@login_required
def equipe_entregadores(request):
    if request.user.perfil.tipo_usuario != 'ENTREGADORA' and not request.user.is_superuser:
        messages.error(request, "Acesso restrito à Transportadora.")
        return redirect('dashboard')

    if request.method == 'POST':
        nome = request.POST.get('nome')
        telefone = request.POST.get('telefone')
        cpf = request.POST.get('cpf')
        cnh = request.POST.get('cnh')
        veiculo = request.POST.get('veiculo')
        placa = request.POST.get('placa')
        
        username_auto = f"motoboy_{nome.split()[0].lower()}_{timezone.now().strftime('%M%S')}"
        
        try:
            novo_user = User.objects.create_user(username=username_auto, password='123', first_name=nome)
            
            perfil = novo_user.perfil
            perfil.tipo_usuario = 'ENTREGADORA'
            perfil.telefone_contato = telefone
            perfil.cpf = cpf
            perfil.cnh = cnh
            perfil.veiculo = veiculo
            perfil.placa_veiculo = placa.upper() if placa else ""
            perfil.save()
            
            messages.success(request, f"Motoboy {nome} adicionado à equipe com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao cadastrar motoboy: {e}")
            
        return redirect('equipe_entregadores')

    # 🌟 CORREÇÃO 1: Esconde o Operador logado (sid) da lista da Frota
    equipe = User.objects.filter(perfil__tipo_usuario='ENTREGADORA', is_active=True).exclude(id=request.user.id).order_by('first_name')
    return render(request, 'gestao/equipe_entregadores.html', {'equipe': equipe})

@login_required
@require_POST
def excluir_entregador(request, id):
    if request.user.perfil.tipo_usuario != 'ENTREGADORA' and not request.user.is_superuser:
        return redirect('dashboard')
        
    # 🌟 CORREÇÃO 2: Trava de segurança para impedir auto-exclusão
    if id == request.user.id:
        messages.error(request, "Erro: Você não pode remover a sua própria conta de Operador Central!")
        return redirect('equipe_entregadores')
        
    entregador = get_object_or_404(User, id=id)
    nome = entregador.first_name or entregador.username
    
    entregador.is_active = False 
    entregador.save()
    
    messages.warning(request, f"Entregador {nome} desativado da frota.")
    return redirect('equipe_entregadores')

@login_required
def mudar_status_entrega(request, id, status):
    pedido = get_object_or_404(Pedido, id=id)
    if status in ['EM_ROTA', 'ENTREGUE']:
        pedido.status_entrega = status
        
        if status == 'EM_ROTA':
            pedido.data_saida_entrega = timezone.now()
            pedido.operador_despacho = request.user
            
            # 🌟 CORREÇÃO 3: Obriga a escolha de um Motoboy real
            if request.method == 'POST':
                entregador_id = request.POST.get('entregador_id')
                if entregador_id:
                    pedido.entregador_responsavel = get_object_or_404(User, id=entregador_id)
                else:
                    messages.error(request, "Por favor, selecione qual motoboy vai fazer esta entrega!")
                    return redirect('painel_entregas')
            else:
                messages.error(request, "Ação inválida. Selecione o motoboy pelo formulário.")
                return redirect('painel_entregas')

        elif status == 'ENTREGUE':
            pedido.data_entregue = timezone.now()
            
        pedido.save()
        messages.success(request, f"Status atualizado para: {pedido.get_status_entrega_display()}")
        
    return redirect('painel_entregas')