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
    
    # Campo para o ID automático (Ex: SID001)
    codigo_identificador = models.CharField(max_length=20, unique=True, blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    tipo_usuario = models.CharField(max_length=20, choices=TIPOS_USUARIO, default='LOJISTA')
    
    # Informações da Empresa
    nome_empresa = models.CharField(max_length=100, blank=True, null=True,unique=True, help_text="Nome da Loja ou Transportadora")
    telefone_contato = models.CharField(max_length=20, blank=True, null=True)
    ativo = models.BooleanField(default=True, verbose_name="Conta Ativa?")

    def __str__(self):
        return f"{self.user.username} - {self.get_tipo_usuario_display()}"
    
    def save(self, *args, **kwargs):
        """
        Lógica corrigida: usa o ID real do banco para gerar o código SID único.
        """
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        # Gera o código apenas se for uma nova conta e ainda não tiver um
        if is_new and not self.codigo_identificador:
            self.codigo_identificador = f"SID{self.id:03d}"
            # Salva apenas o campo de identificação para evitar loops
            super().save(update_fields=['codigo_identificador'])

# Signals consolidados para evitar erros de integridade no cadastro
@receiver(post_save, sender=User)
def gerenciar_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance)
    else:
        if hasattr(instance, 'perfil'):
            instance.perfil.save()


# ==============================================================================
# 2. CATEGORIAS E CONFIGURAÇÕES
# ==============================================================================
class Categoria(models.Model):
    nome = models.CharField(max_length=50, verbose_name="Nome da Categoria")
    # Cada loja tem suas próprias categorias para não misturar
    loja = models.ForeignKey(User, on_delete=models.CASCADE, related_name='minhas_categorias', null=True)
    
    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        # Impede nomes iguais de categorias apenas para a mesma loja
        unique_together = ('nome', 'loja')

    def __str__(self):
        return f"{self.nome} ({self.loja.username if self.loja else 'Global'})"

class Configuracao(models.Model):
    # Vincula as configurações (horário, metas) diretamente ao dono da loja
    loja = models.OneToOneField(User, on_delete=models.CASCADE, related_name='configuracao', null=True)
    nome_empresa = models.CharField(max_length=100, default="Minha Empresa")
    foto_capa = models.ImageField(upload_to='config/', null=True, blank=True)
    visualizacoes_cardapio = models.IntegerField(default=0)
    horario_abertura = models.TimeField(default='08:00')
    horario_fechamento = models.TimeField(default='18:00')
    meta_diaria = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)
    
    # Dias de funcionamento
    segunda = models.BooleanField(default=True)
    terca = models.BooleanField(default=True)
    quarta = models.BooleanField(default=True)
    quinta = models.BooleanField(default=True)
    sexta = models.BooleanField(default=True)
    sabado = models.BooleanField(default=True)
    domingo = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nome_empresa

# O Signal deve ficar após os modelos para que ele reconheça a 'Configuracao'
@receiver(post_save, sender=User)
def gerenciar_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        # Cria o Perfil e a Configuração inicial para a nova loja automaticamente
        Perfil.objects.create(user=instance)
        Configuracao.objects.create(loja=instance, nome_empresa=instance.username)
    else:
        if hasattr(instance, 'perfil'):
            instance.perfil.save()
        if hasattr(instance, 'configuracao'):
            instance.configuracao.save()



# ==============================================================================
# 3. ESTOQUE E PRODUTOS (RESTALRADO E SEM DUPLICIDADE)
# ==============================================================================
class Insumo(models.Model):
    UNIDADES = [('kg', 'Quilo'), ('g', 'Grama'), ('un', 'Unidade'), ('l', 'Litro')]
    nome = models.CharField(max_length=100, verbose_name="Nome do Insumo")
    loja = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meus_insumos', null=True)
    
    # --- Campos restaurados para evitar o FieldError ---
    quantidade_atual = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Qtd em Estoque")
    unidade_medida = models.CharField(max_length=5, choices=UNIDADES, default='un', verbose_name="Unidade")
    preco_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Preço de Compra")
    data_entrada = models.DateField(null=True, blank=True, verbose_name="Data de Entrada")
    data_validade = models.DateField(null=True, blank=True, verbose_name="Data de Validade")
    
    def __str__(self):
        return self.nome

class Produto(models.Model):
    # Apenas uma definição de Produto
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
    finalizado = models.BooleanField(default=False)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Endereço
    telefone = models.CharField(max_length=20, null=True, blank=True)
    rua = models.CharField(max_length=255, null=True, blank=True, verbose_name="Rua/Alameda")
    bairro = models.CharField(max_length=100, null=True, blank=True, verbose_name="Bairro")
    numero = models.CharField(max_length=20, null=True, blank=True, verbose_name="Número/Lote")
    
    OPCOES_PAGAMENTO = [('credito', 'Cartão de Crédito'), ('debito', 'Cartão de Débito'), ('dinheiro', 'Dinheiro')]
    forma_pagamento = models.CharField(max_length=20, choices=OPCOES_PAGAMENTO, null=True, blank=True)

    # Lógica para Entregadoras
    solicitar_entrega = models.BooleanField(default=False, verbose_name="Solicitar Entregadora?")
    
    STATUS_PEDIDO_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PREPARANDO', 'Preparando'),
        ('PRONTO', 'Pronto para Entrega'),
        ('CANCELADO', 'Cancelado'),
    ]
    status_pedido = models.CharField(
        max_length=20, 
        choices=STATUS_PEDIDO_CHOICES, 
        default='PENDENTE'
    )
    
    # 1. ADICIONE ESTA LISTA AQUI:
    STATUS_ENTREGA = [
        ('AGUARDANDO', 'Aguardando Entregador'),
        ('EM_ROTA', 'Em Rota'),
        ('ENTREGUE', 'Entregue'),
    ]
    
    # 2. O seu campo já estava aqui, agora ele vai achar a lista de cima!
    status_entrega = models.CharField(
        max_length=20, 
        choices=STATUS_ENTREGA, 
        default='AGUARDANDO', 
        blank=True, 
        null=True
    )
    
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