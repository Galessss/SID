from django.db import models
from django.utils import timezone

# 1. CATEGORIA
class Categoria(models.Model):
    nome = models.CharField(max_length=50, unique=True, verbose_name="Nome da Categoria")
    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
    def __str__(self):
        return self.nome

# 2. CONFIGURAÇÃO
class Configuracao(models.Model):
    nome_empresa = models.CharField(max_length=100, default="Minha Empresa")
    foto_capa = models.ImageField(upload_to='config/', null=True, blank=True)
    visualizacoes_cardapio = models.IntegerField(default=0)
    horario_abertura = models.TimeField(default='08:00')
    horario_fechamento = models.TimeField(default='18:00')
    meta_diaria = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)
    segunda = models.BooleanField(default=True)
    terca = models.BooleanField(default=True)
    quarta = models.BooleanField(default=True)
    quinta = models.BooleanField(default=True)
    sexta = models.BooleanField(default=True)
    sabado = models.BooleanField(default=True)
    domingo = models.BooleanField(default=True)
    def __str__(self):
        return self.nome_empresa

# 3. INSUMO (NOVO - Matéria Prima)
class Insumo(models.Model):
    UNIDADES = [('kg', 'Quilo'), ('g', 'Grama'), ('un', 'Unidade'), ('l', 'Litro')]
    nome = models.CharField(max_length=100, verbose_name="Nome do Insumo")
    quantidade_atual = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Qtd em Estoque")
    unidade_medida = models.CharField(max_length=5, choices=UNIDADES, default='un', verbose_name="Unidade")
    preco_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Preço de Compra")
    data_entrada = models.DateField(null=True, blank=True, verbose_name="Data de Entrada")
    data_validade = models.DateField(null=True, blank=True, verbose_name="Data de Validade")
    def __str__(self):
        return self.nome

# 4. PRODUTO (Cardápio)
class Produto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(verbose_name="Descrição")
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço")
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='produtos', verbose_name="Categoria")
    foto = models.ImageField(upload_to='produtos/', blank=True, null=True)
    ativo = models.BooleanField(default=True)
    def __str__(self):
        return self.nome

# 5. PEDIDO
class Pedido(models.Model):
    sessao_id = models.CharField(max_length=50, null=True, blank=True)
    nome_cliente = models.CharField(max_length=100, null=True, blank=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    rua = models.CharField(max_length=255, null=True, blank=True, verbose_name="Rua/Alameda")
    bairro = models.CharField(max_length=100, null=True, blank=True, verbose_name="Bairro")
    numero = models.CharField(max_length=20, null=True, blank=True, verbose_name="Número/Lote")
    OPCOES_PAGAMENTO = [('credito', 'Cartão de Crédito'), ('debito', 'Cartão de Débito'), ('dinheiro', 'Dinheiro')]
    forma_pagamento = models.CharField(max_length=20, choices=OPCOES_PAGAMENTO, null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    finalizado = models.BooleanField(default=False)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    def __str__(self):
        return f"Pedido #{self.id} - {self.nome_cliente}"

# 6. ITEM PEDIDO
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