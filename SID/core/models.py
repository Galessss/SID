from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# ==============================================================================
# 1. PERFIL DE USUÁRIO (Controle de Níveis de Acesso e IDs Únicos)
# ==============================================================================
class Perfil(models.Model):
    TIPOS_USUARIO = [
        ('ADMIN', 'Admin Geral'),
        ('LOJISTA', 'Lojista'),
        ('ENTREGADORA', 'Empresa de Entrega'),
    ]
    
    codigo_identificador = models.CharField(max_length=20, unique=True, blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    tipo_usuario = models.CharField(max_length=20, choices=TIPOS_USUARIO, default='LOJISTA')
    
    nome_empresa = models.CharField(max_length=100, blank=True, null=True,unique=True, help_text="Nome da Loja ou Transportadora")
    telefone_contato = models.CharField(max_length=20, blank=True, null=True)
    ativo = models.BooleanField(default=True, verbose_name="Conta Ativa?")

    # ==========================================
    # NOVOS CAMPOS: FICHA CADASTRAL DO MOTOBOY
    # ==========================================
    cpf = models.CharField(max_length=14, blank=True, null=True, verbose_name="CPF")
    cnh = models.CharField(max_length=20, blank=True, null=True, verbose_name="CNH")
    veiculo = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tipo de Veículo")
    placa_veiculo = models.CharField(max_length=10, blank=True, null=True, verbose_name="Placa do Veículo")

    def __str__(self):
        return f"{self.user.username} - {self.get_tipo_usuario_display()}"
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        if is_new and not self.codigo_identificador:
            self.codigo_identificador = f"SID{self.id:03d}"
            super().save(update_fields=['codigo_identificador'])

# ==============================================================================
# 2. CATEGORIAS E CONFIGURAÇÕES
# ==============================================================================
class Categoria(models.Model):
    nome = models.CharField(max_length=50, verbose_name="Nome da Categoria")
    loja = models.ForeignKey(User, on_delete=models.CASCADE, related_name='minhas_categorias', null=True)
    
    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        unique_together = ('nome', 'loja')

    def __str__(self):
        return f"{self.nome} ({self.loja.username if self.loja else 'Global'})"

class Configuracao(models.Model):
    loja = models.OneToOneField(User, on_delete=models.CASCADE, related_name='configuracao', null=True)
    nome_empresa = models.CharField(max_length=100, default="Minha Empresa")
    foto_capa = models.ImageField(upload_to='config/', null=True, blank=True)
    meta_diaria = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    visualizacoes_cardapio = models.PositiveIntegerField(default=0)
    loja_aberta = models.BooleanField(default=True, verbose_name="Loja Aberta Manualmente")
    
    # Dias e Horários de funcionamento
    segunda = models.BooleanField(default=True)
    terca = models.BooleanField(default=True)
    quarta = models.BooleanField(default=True)
    quinta = models.BooleanField(default=True)
    sexta = models.BooleanField(default=True)
    sabado = models.BooleanField(default=True)
    domingo = models.BooleanField(default=True)
    segunda_abertura = models.TimeField(null=True, blank=True)
    segunda_fechamento = models.TimeField(null=True, blank=True)
    terca_abertura = models.TimeField(null=True, blank=True)
    terca_fechamento = models.TimeField(null=True, blank=True)
    quarta_abertura = models.TimeField(null=True, blank=True)
    quarta_fechamento = models.TimeField(null=True, blank=True)
    quinta_abertura = models.TimeField(null=True, blank=True)
    quinta_fechamento = models.TimeField(null=True, blank=True)
    sexta_abertura = models.TimeField(null=True, blank=True)
    sexta_fechamento = models.TimeField(null=True, blank=True)
    sabado_abertura = models.TimeField(null=True, blank=True)
    sabado_fechamento = models.TimeField(null=True, blank=True)
    domingo_abertura = models.TimeField(null=True, blank=True)
    domingo_fechamento = models.TimeField(null=True, blank=True)
    
    def __str__(self):
        return self.nome_empresa

# ==============================================================================
# 3. ESTOQUE E PRODUTOS 
# ==============================================================================
class Insumo(models.Model):
    UNIDADES = [('kg', 'Quilo'), ('g', 'Grama'), ('un', 'Unidade'), ('l', 'Litro')]
    nome = models.CharField(max_length=100, verbose_name="Nome do Insumo")
    loja = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meus_insumos', null=True)
    quantidade_atual = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Qtd em Estoque")
    unidade_medida = models.CharField(max_length=5, choices=UNIDADES, default='un', verbose_name="Unidade")
    preco_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Preço de Compra")
    data_entrada = models.DateField(null=True, blank=True, verbose_name="Data de Entrada")
    data_validade = models.DateField(null=True, blank=True, verbose_name="Data de Validade")
    
    def __str__(self):
        return self.nome

class Produto(models.Model):
    loja = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meus_produtos', null=True)
    nome = models.CharField(max_length=100)
    descricao = models.TextField(verbose_name="Descrição")
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço")
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='produtos', verbose_name="Categoria")
    foto = models.ImageField(upload_to='produtos/', blank=True, null=True)
    ativo = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nome
    
# ==============================================================================
# 4. PEDIDOS E ENTREGA (LOGÍSTICA)
# ==============================================================================
class Pedido(models.Model):
    sessao_id = models.CharField(max_length=50, null=True, blank=True)
    loja = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meus_pedidos', null=True)
    nome_cliente = models.CharField(max_length=100, null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    operador_despacho = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='despachos_realizados', verbose_name="Operador que despachou")
    data_entregue = models.DateTimeField(null=True, blank=True, verbose_name="Hora que foi entregue")
    finalizado = models.BooleanField(default=False)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    data_saida_entrega = models.DateTimeField(null=True, blank=True, verbose_name="Hora que saiu para entrega")
    sessao_id = models.CharField(max_length=50, null=True, blank=True)
    loja = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meus_pedidos', null=True)
    nome_cliente = models.CharField(max_length=100, null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)


    telefone = models.CharField(max_length=20, null=True, blank=True)
    rua = models.CharField(max_length=255, null=True, blank=True, verbose_name="Rua/Alameda")
    bairro = models.CharField(max_length=100, null=True, blank=True, verbose_name="Bairro")
    numero = models.CharField(max_length=20, null=True, blank=True, verbose_name="Número/Lote")
    
    OPCOES_PAGAMENTO = [('credito', 'Cartão de Crédito'), ('debito', 'Cartão de Débito'), ('dinheiro', 'Dinheiro')]
    forma_pagamento = models.CharField(max_length=20, choices=OPCOES_PAGAMENTO, null=True, blank=True)

    solicitar_entrega = models.BooleanField(default=False, verbose_name="Solicitar Entregadora?")
    
    STATUS_PEDIDO_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PREPARANDO', 'Preparando'),
        ('PRONTO', 'Pronto para Entrega'),
        ('CANCELADO', 'Cancelado'),
    ]
    status_pedido = models.CharField(max_length=20, choices=STATUS_PEDIDO_CHOICES, default='PENDENTE')
    
    STATUS_ENTREGA = [
        ('AGUARDANDO', 'Aguardando Entregador'),
        ('EM_ROTA', 'Em Rota'),
        ('ENTREGUE', 'Entregue'),
    ]
    status_entrega = models.CharField(max_length=20, choices=STATUS_ENTREGA, default='AGUARDANDO', blank=True, null=True)
    entregador_responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='entregas')

    def __str__(self):
        return f"Pedido #{self.id} - {self.nome_cliente}"

class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    preco = models.DecimalField(max_digits=10, decimal_places=2) 
    
    @property
    def subtotal(self):
        return self.quantidade * self.preco
        
    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome}"
    
# ==============================================================================
# 5. GESTÃO AUTOMÁTICA DE USUÁRIOS (SINAL ÚNICO)
# ==============================================================================
@receiver(post_save, sender=User)
def gerenciar_dados_usuario(sender, instance, created, **kwargs):
    if created:
        # get_or_create garante que NUNCA vai tentar criar dois perfis para a mesma pessoa
        Perfil.objects.get_or_create(user=instance)
        Configuracao.objects.get_or_create(loja=instance, defaults={'nome_empresa': instance.username})
    else:
        # Salva o perfil e a configuração nas edições posteriores
        if hasattr(instance, 'perfil'):
            instance.perfil.save()
        if hasattr(instance, 'configuracao'):
            instance.configuracao.save()