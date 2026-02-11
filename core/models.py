from django.db import models
from django.utils import timezone

class Produto(models.Model):
    CATEGORIAS_CHOICES = [
        ('lanches', 'Lanches / Pratos'),
        ('bebidas', 'Bebidas'),
        ('sobremesas', 'Sobremesas'),
        ('porcoes', 'Porções / Extras'),
    ]
    nome = models.CharField(max_length=100)
    descricao = models.TextField(verbose_name="Descrição")
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço")
    categoria = models.CharField(max_length=20, choices=CATEGORIAS_CHOICES, default='lanches', verbose_name="Categoria")
    foto = models.ImageField(upload_to='produtos/', blank=True, null=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

class Configuracao(models.Model):
    nome_empresa = models.CharField(max_length=100, default="SID Burguer & Co.")
    foto_capa = models.ImageField(upload_to='config/', blank=True, null=True)
    horario_abertura = models.TimeField(default="18:00")
    horario_fechamento = models.TimeField(default="23:00")
    segunda = models.BooleanField(default=True)
    terca = models.BooleanField(default=True)
    quarta = models.BooleanField(default=True)
    quinta = models.BooleanField(default=True)
    sexta = models.BooleanField(default=True)
    sabado = models.BooleanField(default=True)
    domingo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome_empresa

class Pedido(models.Model):
    data_criacao = models.DateTimeField(auto_now_add=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    finalizado = models.BooleanField(default=False)

class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    preco_momento = models.DecimalField(max_digits=10, decimal_places=2) 

    @property
    def subtotal(self):
        return self.quantidade * self.preco_momento