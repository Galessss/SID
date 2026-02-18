from django import forms
from .models import Produto, Configuracao, Categoria, Insumo

# =============================================================================
# 1. FORMULÁRIO DE PRODUTOS (CARDÁPIO)
# =============================================================================
class ProdutoForm(forms.ModelForm):
    # Campo auxiliar para criar categorias dinamicamente
    nova_categoria = forms.CharField(
        max_length=100, 
        required=False, 
        label="Ou Nova Categoria", 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite para criar uma nova'
        })
    )

    class Meta:
        model = Produto
        # Mantenha apenas os campos que existem no modelo Produto
        fields = ['nome', 'descricao', 'preco', 'categoria', 'foto', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'preco': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'foto': forms.FileInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super(ProdutoForm, self).__init__(*args, **kwargs)
        # Permite que a categoria seja opcional caso o usuário use o campo 'nova_categoria'
        self.fields['categoria'].required = False

    def clean(self):
        cleaned_data = super().clean()
        categoria = cleaned_data.get('categoria')
        nova_categoria = cleaned_data.get('nova_categoria')

        if not categoria and not nova_categoria:
            raise forms.ValidationError("Selecione uma categoria existente ou digite uma nova.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        nova_cat_nome = self.cleaned_data.get('nova_categoria')

        if nova_cat_nome:
            # Busca ou cria a categoria para evitar duplicidade
            categoria_obj, created = Categoria.objects.get_or_create(
                nome__iexact=nova_cat_nome,
                defaults={'nome': nova_cat_nome}
            )
            instance.categoria = categoria_obj
        
        if commit:
            instance.save()
        return instance


# =============================================================================
# 2. FORMULÁRIO DE INSUMOS (ESTOQUE DE MATÉRIA-PRIMA)
# =============================================================================
class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = ['nome', 'quantidade_atual', 'unidade_medida', 'preco_compra', 'data_entrada', 'data_validade']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'quantidade_atual': forms.NumberInput(attrs={'class': 'form-control'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'preco_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'data_entrada': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_validade': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }


# =============================================================================
# 3. FORMULÁRIO DE CONFIGURAÇÃO
# =============================================================================
class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = Configuracao
        fields = [
            'nome_empresa', 'foto_capa', 'horario_abertura', 'horario_fechamento',
            'meta_diaria', 'segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo'
        ]
        widgets = {
            'horario_abertura': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_fechamento': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'meta_diaria': forms.NumberInput(attrs={'class': 'form-control'}),
            'nome_empresa': forms.TextInput(attrs={'class': 'form-control'}),
        }