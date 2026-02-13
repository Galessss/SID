from django.db import models
from django.utils import timezone

# 1. MODELO: Categoria
class Categoria(models.Model):
    nome = models.CharField(max_length=50, unique=True, verbose_name="Nome da Categoria")

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.nome


# 2. MODELO: Configuração
class Configuracao(models.Model):
    nome_empresa = models.CharField(max_length=100, default="Minha Empresa")
    foto_capa = models.ImageField(upload_to='config/', null=True, blank=True)
    visualizacoes_cardapio = models.IntegerField(default=0)
    
    horario_abertura = models.TimeField(default='08:00')
    horario_fechamento = models.TimeField(default='18:00')
    
    meta_diaria = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)

    # Dias da semana
    segunda = models.BooleanField(default=True)
    terca = models.BooleanField(default=True)
    quarta = models.BooleanField(default=True)
    quinta = models.BooleanField(default=True)
    sexta = models.BooleanField(default=True)
    sabado = models.BooleanField(default=True)
    domingo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome_empresa


# 3. MODELO: Produto
class Produto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(verbose_name="Descrição")
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço")
    
    categoria = models.ForeignKey(
        Categoria, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='produtos',
        verbose_name="Categoria"
    )
    
    foto = models.ImageField(upload_to='produtos/', blank=True, null=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


# core/models.py

class Pedido(models.Model):
    # Campos existentes
    sessao_id = models.CharField(max_length=50, null=True, blank=True)
    nome_cliente = models.CharField(max_length=100, null=True, blank=True)
    
    # NOVOS CAMPOS DE ENTREGA
    telefone = models.CharField(max_length=20, null=True, blank=True)
    rua = models.CharField(max_length=255, null=True, blank=True, verbose_name="Rua/Alameda")
    bairro = models.CharField(max_length=100, null=True, blank=True, verbose_name="Bairro")
    numero = models.CharField(max_length=20, null=True, blank=True, verbose_name="Número/Lote")
    
    # FORMA DE PAGAMENTO
    OPCOES_PAGAMENTO = [
        ('credito', 'Cartão de Crédito'),
        ('debito', 'Cartão de Débito'),
        ('dinheiro', 'Dinheiro'),
    ]
    forma_pagamento = models.CharField(max_length=20, choices=OPCOES_PAGAMENTO, null=True, blank=True)
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    finalizado = models.BooleanField(default=False)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Pedido #{self.id} - {self.nome_cliente}"


# 5. MODELO: Item do Pedido
class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    # Usei 'preco' para manter compatibilidade com a view criada anteriormente
    preco = models.DecimalField(max_digits=10, decimal_places=2) 

    @property
    def subtotal(self):
        return self.quantidade * self.preco
    
    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome}"
    
    