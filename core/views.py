import json
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User  # IMPORTANTE: Corrige o erro do Admin
from django.db.models import Sum, Prefetch
from django.utils import timezone
from django.http import JsonResponse
from django.contrib import messages
from django.utils.text import slugify
import datetime
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from .models import Perfil, Categoria, Configuracao

# Seus Models e Forms
from .models import Produto, Pedido, ItemPedido, Configuracao, Categoria, Insumo, Perfil
from .forms import ProdutoForm, InsumoForm, NovoUsuarioForm, ConfiguracaoForm

# =============================================================================
# 1. AUTENTICAÇÃO E LOGIN
# =============================================================================

def login_view(request):
    # Se já estiver logado, redireciona para a área correta
    if request.user.is_authenticated:
        if request.user.is_superuser or (hasattr(request.user, 'perfil') and request.user.perfil.tipo_usuario == 'ADMIN'):
            return redirect('dashboard_admin')
        elif hasattr(request.user, 'perfil') and request.user.perfil.tipo_usuario == 'ENTREGADORA':
            return redirect('painel_entregas')
        else:
            return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # SEGURANÇA: Cria perfil se não existir (para usuários antigos)
                if not hasattr(user, 'perfil'):
                    tipo = 'ADMIN' if user.is_superuser else 'LOJISTA'
                    Perfil.objects.create(user=user, tipo_usuario=tipo)
                
                # Redirecionamento Baseado no Perfil
                if user.is_superuser or user.perfil.tipo_usuario == 'ADMIN':
                    return redirect('dashboard_admin')
                elif user.perfil.tipo_usuario == 'ENTREGADORA':
                    return redirect('painel_entregas')
                else:
                    return redirect('dashboard')
            else:
                messages.error(request, "Usuário ou senha inválidos.")
        else:
            messages.error(request, "Erro no formulário.")
    else:
        form = AuthenticationForm() # Corrige o erro 'form not defined'

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

    # Busca todos os usuários (menos o próprio admin)
    usuarios = User.objects.all().exclude(id=request.user.id).select_related('perfil').order_by('-date_joined')
    form = NovoUsuarioForm()

    return render(request, 'gestao/dashboard_admin.html', {'usuarios': usuarios, 'form': form})

@login_required
def admin_criar_usuario(request):
    if request.method == 'POST':
        form = NovoUsuarioForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, f'Usuário "{user.username}" criado com sucesso!')
            except Exception as e:
                # Caso ocorra um erro inesperado no banco de dados
                messages.error(request, f'Erro no banco de dados: {str(e)}')
        else:
            # Captura cada erro específico do formulário
            for field, errors in form.errors.items():
                for error in errors:
                    # 'field' é o nome do campo (ex: username) e 'error' é a mensagem
                    nome_campo = form.fields[field].label or field
                    messages.error(request, f"Erro em {nome_campo}: {error}")
            
            # Log no terminal para você debugar se necessário
            print(f"Erros detalhados: {form.errors.as_data()}")
            
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


# =============================================================================
# 3. GESTÃO LOJISTA (DASHBOARD)
# =============================================================================

@login_required
def dashboard_gestor(request):
    # Bloqueia entregadores de verem o dashboard financeiro
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo_usuario == 'ENTREGADORA':
        return redirect('painel_entregas')

    config = Configuracao.objects.filter(id=1).first()
    hoje = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    def calcular_faturamento(data_inicio):
        return Pedido.objects.filter(
            data_criacao__gte=data_inicio, 
            finalizado=True
        ).aggregate(total=Sum('valor_total'))['total'] or 0

    faturamento_hoje = calcular_faturamento(hoje)
    faturamento_total = Pedido.objects.filter(finalizado=True).aggregate(total=Sum('valor_total'))['total'] or 0
    total_pedidos = Pedido.objects.filter(finalizado=True).count()
    visitas = config.visualizacoes_cardapio if config else 0
    
    # Meta
    meta = float(config.meta_diaria) if config and config.meta_diaria else 1000.0
    porcentagem_meta = (float(faturamento_hoje) / meta) * 100 if meta > 0 else 0
    progresso_barra = min(porcentagem_meta, 100)

    # Gráfico
    top_produtos_raw = ItemPedido.objects.filter(pedido__finalizado=True)\
        .values('produto__nome')\
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
    
    # Lista de Pedidos recentes para o Dashboard
    ultimos_pedidos = Pedido.objects.filter(finalizado=True).order_by('-data_criacao')[:10]

    context = {
        'faturamento_total': faturamento_total,
        'total_pedidos': total_pedidos,
        'visitas': visitas,
        'faturamento_hoje': faturamento_hoje,
        'meta': meta,
        'porcentagem_meta': round(porcentagem_meta, 1),
        'progresso_barra': progresso_barra,
        'faturamento_semanal': calcular_faturamento(hoje - timedelta(days=7)),
        'faturamento_mensal': calcular_faturamento(hoje.replace(day=1)),
        'config': config,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_datasets_json': json.dumps(chart_datasets),
        'ultimos_pedidos': ultimos_pedidos, # Passando pedidos para a tabela
    }
    
    return render(request, 'gestao/dashboard.html', context)


# =============================================================================
# 4. PRODUTOS (CARDÁPIO)
# =============================================================================
@login_required
def editar_produto(request, id):
    # 1. Busca o produto garantindo a segurança da loja
    produto = get_object_or_404(Produto, id=id, loja=request.user)
    
    if request.method == 'POST':
        # No POST, passamos os dados, os arquivos, a instância e o usuário
        form = ProdutoForm(request.POST, request.FILES, instance=produto, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('produtos')
    else:
        # 2. NO GET: É aqui que o formulário é "carregado" para a tela
        # Se você esquecer o 'instance', os campos virão vazios.
        # Se você esquecer o 'user', o __init__ do form pode dar erro.
        form = ProdutoForm(instance=produto, user=request.user)
    
    # 3. O nome da chave no dicionário deve ser 'form' (como no seu HTML)
    return render(request, 'gestao/editar_produto.html', {
        'form': form, 
        'produto': produto
    })

@login_required
def editar_produto(request, id):
    # 1. Busca o produto garantindo que ele pertence à loja logada
    produto = get_object_or_404(Produto, id=id, loja=request.user)
    
    if request.method == 'POST':
        # 2. Passa o 'user' para o formulário validar as categorias daquela loja
        form = ProdutoForm(request.POST, request.FILES, instance=produto, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('produtos')
    else:
        # 3. NO "GET": É aqui que o formulário é criado para ser exibido na tela
        form = ProdutoForm(instance=produto, user=request.user)
    
    # O dicionário deve conter a chave 'form' exatamente como usada no HTML
    return render(request, 'gestao/editar_produto.html', {
        'form': form, 
        'produto': produto
    })

@login_required
def deletar_produto(request, id):
    # SEGURANÇA: Garante que ninguém apague o produto de outra loja
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
            form.save()
            messages.success(request, 'Insumo cadastrado com sucesso!')
            return redirect('estoque_insumos')
        else:
            messages.error(request, 'Erro ao cadastrar. Verifique os dados.')
    else:
        form = InsumoForm()

    insumos = Insumo.objects.all().order_by('data_validade')
    hoje = timezone.now().date()
    return render(request, 'gestao/estoque_insumos.html', {'insumos': insumos, 'form': form, 'hoje': hoje})

@login_required
def editar_insumo(request, id):
    insumo = get_object_or_404(Insumo, id=id)
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
    insumo = get_object_or_404(Insumo, id=id)
    insumo.delete()
    messages.success(request, 'Insumo removido com sucesso.')
    return redirect('estoque_insumos')


# =============================================================================
# 6. LOGÍSTICA E ENTREGAS
# =============================================================================

@login_required
def painel_entregas(request):
    # Apenas Entregadores ou Admins
    try:
        if request.user.perfil.tipo_usuario != 'ENTREGADORA' and not request.user.is_superuser:
            messages.error(request, "Acesso restrito a entregadores.")
            return redirect('dashboard')
    except:
        return redirect('dashboard')

    pedidos = Pedido.objects.filter(
        finalizado=True,
        solicitar_entrega=True
    ).exclude(status_entrega='ENTREGUE').order_by('-data_criacao')

    return render(request, 'gestao/painel_entregas.html', {'pedidos': pedidos})

@login_required
def mudar_status_entrega(request, id, status):
    pedido = get_object_or_404(Pedido, id=id)
    if status in ['EM_ROTA', 'ENTREGUE']:
        pedido.status_entrega = status
        pedido.entregador_responsavel = request.user
        pedido.save()
        messages.success(request, f"Status atualizado para: {pedido.get_status_entrega_display()}")
    return redirect('painel_entregas')

@login_required
def solicitar_entrega_loja(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    pedido.solicitar_entrega = True
    pedido.status_entrega = 'AGUARDANDO'
    pedido.save()
    messages.success(request, f"Entregador solicitado para o Pedido #{pedido.id}!")
    return redirect('dashboard')


# =============================================================================
# 7. CONFIGURAÇÕES E PERFIL
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
# 8. VISÃO PÚBLICA (CARDÁPIO E CARRINHO)
# =============================================================================

def cardapio_view(request):
    config = Configuracao.objects.filter(id=1).first()
    categorias = Categoria.objects.filter(produtos__ativo=True).distinct().prefetch_related(
        Prefetch('produtos', queryset=Produto.objects.filter(ativo=True))
    )

    if config:
        config.visualizacoes_cardapio += 1
        config.save()
        
        agora = timezone.localtime(timezone.now())
        hora_atual = agora.time()
        dia_semana_index = agora.weekday()
        
        dias_semana = [
            {'nome': 'Seg', 'aberto': config.segunda},
            {'nome': 'Ter', 'aberto': config.terca},
            {'nome': 'Qua', 'aberto': config.quarta},
            {'nome': 'Qui', 'aberto': config.quinta},
            {'nome': 'Sex', 'aberto': config.sexta},
            {'nome': 'Sáb', 'aberto': config.sabado},
            {'nome': 'Dom', 'aberto': config.domingo},
        ]
        
        aberto_hoje = dias_semana[dia_semana_index]['aberto']
        motivo_fechado = ""
        loja_aberta_agora = False
        
        if not aberto_hoje:
            motivo_fechado = "Hoje não abrimos."
        else:
            if config.horario_abertura < config.horario_fechamento:
                loja_aberta_agora = config.horario_abertura <= hora_atual <= config.horario_fechamento
            else:
                loja_aberta_agora = hora_atual >= config.horario_abertura or hora_atual <= config.horario_fechamento
            
            if not loja_aberta_agora:
                motivo_fechado = f"Abrimos às {config.horario_abertura.strftime('%H:%M')}."

        horario_texto = f"Aberto das {config.horario_abertura.strftime('%H:%M')} às {config.horario_fechamento.strftime('%H:%M')}"
        nome_empresa = config.nome_empresa
        foto_capa = config.foto_capa.url if config.foto_capa else ""
    else:
        nome_empresa, foto_capa, horario_texto, loja_aberta_agora, motivo_fechado = "SID Burguer", "", "", True, ""
        dias_semana = []

    context = {
        'nome_empresa': nome_empresa,
        'horario_funcionamento': horario_texto,
        'dias_semana': dias_semana,
        'esta_aberto_hoje': loja_aberta_agora,
        'motivo_fechado': motivo_fechado,
        'foto_capa': foto_capa,
        'categorias': categorias,
    }
    return render(request, 'core/cardapio.html', context)

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
        
        request.session.flush()
        return render(request, 'core/sucesso.html', {'pedido': pedido})
    return redirect('ver_carrinho')

def limpar_carrinho(request):
    if request.method == 'POST':
        pedido = _get_carrinho(request)
        pedido.delete()
        messages.success(request, 'Carrinho limpo.')
    return redirect('cardapio')


# =============================================================================
# 9. APIS (AJAX)
# =============================================================================

@login_required
@require_POST
def api_criar_categoria(request):
    try:
        dados = json.loads(request.body)
        nome = dados.get('nome')
        if not nome: 
            return JsonResponse({'sucesso': False, 'erro': 'Nome vazio.'})
        
        # Verifica se já existe a categoria PARA ESTA LOJA
        if Categoria.objects.filter(nome__iexact=nome, loja=request.user).exists():
            return JsonResponse({'sucesso': False, 'erro': 'Você já tem essa categoria.'})
        
        # Cria a categoria vinculada ao usuário logado
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
            prod = Produto.objects.get(id=id)
            prod.ativo = not prod.ativo
            prod.save()
            return JsonResponse({'status': 'sucesso', 'ativo': prod.ativo})
        except:
            return JsonResponse({'status': 'erro'}, status=404)
    return JsonResponse({'status': 'erro'}, status=405)

# Compatibilidade
@login_required
def alternar_status_produto(request, id):
    return api_alternar_status(request, id)

@require_POST
def adicionar_item_api(request, produto_id):
    pedido = _get_carrinho(request)
    produto = get_object_or_404(Produto, id=produto_id)
    item, created = ItemPedido.objects.get_or_create(pedido=pedido, produto=produto, defaults={'preco': produto.preco, 'quantidade': 0})
    item.quantidade += 1
    item.save()
    
    valor_total = sum(i.produto.preco * i.quantidade for i in pedido.itens.all())
    pedido.valor_total = valor_total
    pedido.save()
    
    return JsonResponse({
        'status': 'sucesso', 
        'qtd_total': pedido.itens.aggregate(Sum('quantidade'))['quantidade__sum'] or 0,
        'valor_total': valor_total
    })

@login_required
def dashboard_admin(request):
    if not request.user.is_superuser and request.user.perfil.tipo_usuario != 'ADMIN':
        messages.error(request, "Acesso restrito.")
        return redirect('dashboard')

    query = request.GET.get('q')
    # O prefetch_related ajuda a carregar os dados de configuração de forma rápida
    usuarios = User.objects.all().exclude(id=request.user.id).select_related('perfil').order_by('-date_joined')

    if query:
        usuarios = usuarios.filter(
            Q(id__icontains=query) | 
            Q(username__icontains=query) | 
            Q(first_name__icontains=query)
        )

    # Buscamos as configurações de cada empresa para mostrar os horários
    # Nota: No seu modelo atual, a Configuracao é global (ID=1). 
    # Para sistemas multi-lojas, cada lojista teria sua própria FK de Configuração.
    # Por enquanto, pegaremos a configuração global para exibir no painel.
    config_geral = Configuracao.objects.filter(id=1).first()

    form = NovoUsuarioForm()
    return render(request, 'gestao/dashboard_admin.html', {
        'usuarios': usuarios, 
        'form': form, 
        'config_geral': config_geral
    })

# No core/views.py
from django.http import JsonResponse

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
            'horario': f"{config.horario_abertura.strftime('%H:%M')} - {config.horario_fechamento.strftime('%H:%M')}" if config and u.perfil.tipo_usuario == 'LOJISTA' else "N/A"
        })
    
    return JsonResponse({'usuarios': data})

@login_required
def admin_criar_usuario(request):
    if request.method == 'POST':
        form = NovoUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            
            # Se o username já existir, adicionamos um sufixo numérico
            original_username = user.username
            counter = 1
            while User.objects.filter(username=user.username).exists():
                user.username = f"{original_username}{counter}"
                counter += 1
            
            user.save()
            messages.success(request, f'Usuário {user.username} criado com sucesso!')
        else:
            # Mostra o erro real (ex: "Este nome de usuário já existe")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    return redirect('dashboard_admin')


@login_required
def dashboard_gestor(request):
    # Filtra pedidos apenas da loja logada
    pedidos_loja = Pedido.objects.filter(loja=request.user)
    
    # Busca a configuração específica desta loja
    config, created = Configuracao.objects.get_or_create(loja=request.user)
    
    faturamento_hoje = pedidos_loja.filter(
        data_criacao__gte=timezone.now().date(), 
        finalizado=True
    ).aggregate(total=Sum('valor_total'))['total'] or 0
    
    # ... restante da lógica filtrada
    return render(request, 'gestao/dashboard.html', {'faturamento_hoje': faturamento_hoje, 'config': config})



@login_required
def dashboard_gestor(request):
    # 1. Filtramos a configuração específica desta loja
    config, created = Configuracao.objects.get_or_create(loja=request.user)
    
    hoje = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 2. Blindagem: Filtramos TODOS os pedidos pela loja logada
    meus_pedidos = Pedido.objects.filter(loja=request.user)
    
    faturamento_hoje = meus_pedidos.filter(
        data_criacao__gte=hoje, 
        finalizado=True
    ).aggregate(total=Sum('valor_total'))['total'] or 0

    faturamento_total = meus_pedidos.filter(finalizado=True).aggregate(total=Sum('valor_total'))['total'] or 0
    
    # Gráfico e Tabela também devem ser filtrados
    ultimos_pedidos = meus_pedidos.filter(finalizado=True).order_by('-data_criacao')[:10]

    context = {
        'faturamento_total': faturamento_total,
        'faturamento_hoje': faturamento_hoje,
        'config': config,
        'ultimos_pedidos': ultimos_pedidos,
    }
    return render(request, 'gestao/dashboard.html', context)


@login_required
def estoque_insumos_view(request):
    if request.method == 'POST':
        form = InsumoForm(request.POST)
        if form.is_valid():
            insumo = form.save(commit=False)
            insumo.loja = request.user # Garante o isolamento do insumo
            insumo.save()
            return redirect('estoque_insumos')

    # Lista apenas os insumos desta loja específica
    insumos = Insumo.objects.filter(loja=request.user).order_by('data_validade')
    return render(request, 'gestao/estoque_insumos.html', {'insumos': insumos})

@login_required
def produtos_view(request):
    """
    Função que renderiza a página de gestão de produtos.
    Certifique-se de que o nome é exatamente 'produtos_view'.
    """
    if request.method == 'POST':
        # Passamos o usuário logado para o formulário filtrar as categorias
        form = ProdutoForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            produto = form.save(commit=False)
            produto.loja = request.user  # Blindagem: define o dono do produto
            produto.save()
            messages.success(request, "Produto cadastrado com sucesso!")
            return redirect('produtos')
    else:
        # No carregamento inicial, também passamos o usuário
        form = ProdutoForm(user=request.user)

    # Filtra apenas os produtos da loja logada para evitar mistura de dados
    lista_produtos = Produto.objects.filter(loja=request.user).order_by('nome')
    total_produtos = lista_produtos.count()

    return render(request, 'gestao/produtos.html', {
        'form': form,
        'lista_produtos': lista_produtos,
        'total_produtos': total_produtos
    })

def cardapio_publico(request, nome_empresa_slug):
    # 1. Identificamos a loja pela URL
    perfil = get_object_or_404(Perfil, nome_empresa__iexact=nome_empresa_slug.replace('-', ' '))
    loja_dona = perfil.user

    # 2. FILTRAGEM DUPLA: Categorias da loja + Produtos DAQUELA loja dentro da categoria
    # Usamos o Prefetch para criar um atributo 'produtos_filtrados' que só contém itens do dono
    categorias = Categoria.objects.filter(loja=loja_dona).prefetch_related(
        Prefetch(
            'produtos', 
            queryset=Produto.objects.filter(loja=loja_dona, ativo=True),
            to_attr='produtos_da_loja' # Nome que usaremos no HTML
        )
    ).distinct()

    config = Configuracao.objects.filter(loja=loja_dona).first()

    context = {
        'nome_empresa': perfil.nome_empresa,
        'categorias': categorias,
        'config': config,
        # ... outros dados de horário
    }
    return render(request, 'gestao/cardapio.html', context)