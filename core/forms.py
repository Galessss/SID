from django import forms
from .models import Produto, Configuracao, Categoria

class ProdutoForm(forms.ModelForm):
    # Campo auxiliar para digitar uma nova categoria (não salva direto no Produto)
    nova_categoria = forms.CharField(
        max_length=100,
        required=False,
        label="Ou Nova Categoria",
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Digite para criar uma nova (Ex: Sobremesas)'
        })
    )

    class Meta:
        model = Produto
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
        # Torna o campo de seleção opcional, pois o usuário pode optar por digitar uma nova
        self.fields['categoria'].required = False

    def clean(self):
        cleaned_data = super().clean()
        categoria = cleaned_data.get('categoria')
        nova_categoria = cleaned_data.get('nova_categoria')

        # Validação: O usuário precisa ou selecionar uma existente OU digitar uma nova
        if not categoria and not nova_categoria:
            raise forms.ValidationError("Por favor, selecione uma categoria existente ou digite o nome de uma nova.")
        
        return cleaned_data

    def save(self, commit=True):
        # Pega a instância do produto mas não salva ainda no banco
        instance = super().save(commit=False)
        
        nova_categoria_nome = self.cleaned_data.get('nova_categoria')

        if nova_categoria_nome:
            # Se digitou algo, cria a categoria ou pega se já existir (evita duplicados)
            categoria_obj, created = Categoria.objects.get_or_create(
                nome__iexact=nova_categoria_nome,
                defaults={'nome': nova_categoria_nome}
            )
            # Vincula a nova categoria ao produto
            instance.categoria = categoria_obj
        
        if commit:
            instance.save()
        return instance

class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = Configuracao
        fields = [
            'nome_empresa', 
            'foto_capa', 
            'horario_abertura', 
            'horario_fechamento',
            'meta_diaria',
            'segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo'
        ]