from django.db import models
from django.utils import timezone

from django.db import models

# 1. NOVO MODELO: Categoria
class Categoria(models.Model):
    nome = models.CharField(max_length=50, unique=True, verbose_name="Nome da Categoria")

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.nome

class Configuracao(models.Model):
    # ... campos anteriores ...
    meta_diaria = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)


# 2. MODELO ATUALIZADO: Produto
class Produto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(verbose_name="Descrição")
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço")
    
    # Agora o campo categoria é uma chave estrangeira
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
    



from django.db import models

# ... outros modelos (Produto, Categoria, etc) ...

class Configuracao(models.Model):
    # Campos existentes...
    nome_empresa = models.CharField(max_length=100, default="Minha Empresa")
    foto_capa = models.ImageField(upload_to='config/', null=True, blank=True)
    visualizacoes_cardapio = models.IntegerField(default=0)
    
    horario_abertura = models.TimeField(default='08:00')
    horario_fechamento = models.TimeField(default='18:00')
    
    # --- ADICIONE ESTE CAMPO ---
    meta_diaria = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)
    # ---------------------------

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
    