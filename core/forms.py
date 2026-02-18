from django import forms
from django.contrib.auth.models import User
from .models import Produto, Configuracao, Categoria, Insumo, Perfil

# =============================================================================
# 1. FORMULÁRIO DE PRODUTOS (CARDÁPIO)
# =============================================================================
class ProdutoForm(forms.ModelForm):
    # Campo extra para criar categorias na hora
    nova_categoria = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'preco', 'categoria', 'foto', 'ativo']
        # Os widgets garantem que o HTML receba as classes de estilo
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'preco': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'foto': forms.FileInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        # Captura o usuário enviado pela View para filtrar as categorias
        self.user = kwargs.pop('user', None)
        super(ProdutoForm, self).__init__(*args, **kwargs)
        if self.user:
            self.fields['categoria'].queryset = Categoria.objects.filter(loja=self.user)

    def clean(self):
        cleaned_data = super().clean()
        categoria = cleaned_data.get('categoria')
        nova_categoria = cleaned_data.get('nova_categoria')

        if not categoria and not nova_categoria:
            raise forms.ValidationError("Selecione uma categoria ou digite uma nova.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        nova_cat_nome = self.cleaned_data.get('nova_categoria')

        if nova_cat_nome and self.user:
            # Busca ou cria a categoria vinculando-a à LOJA logada
            categoria_obj, created = Categoria.objects.get_or_create(
                nome__iexact=nova_cat_nome,
                loja=self.user,
                defaults={'nome': nova_cat_nome, 'loja': self.user}
            )
            instance.categoria = categoria_obj
        
        if commit:
            instance.save()
        return instance

# =============================================================================
# 2. FORMULÁRIO DE INSUMOS
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

# =============================================================================
# 4. FORMULÁRIO DE NOVO USUÁRIO
# =============================================================================
class NovoUsuarioForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label="Senha", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    nome_empresa = forms.CharField(
        max_length=100, 
        required=True, 
        label="Nome da Empresa",
        help_text="Este nome deve ser exclusivo no sistema.",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: SID Burguer'})
    )
    
    tipo_usuario = forms.ChoiceField(
        choices=[('LOJISTA', 'Lojista'), ('ENTREGADORA', 'Entregadora'), ('ADMIN', 'Admin')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Login de acesso'}),
        }

    def clean_nome_empresa(self):
        nome = self.cleaned_data.get('nome_empresa')
        if Perfil.objects.filter(nome_empresa=nome).exists():
            raise forms.ValidationError("Já existe uma empresa cadastrada com este nome.")
        return nome

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        
        username_base = user.username
        contador = 1
        while User.objects.filter(username=user.username).exists():
            user.username = f"{username_base}{contador}"
            contador += 1
        
        if commit:
            user.save()
            if hasattr(user, 'perfil'):
                perfil = user.perfil
                perfil.tipo_usuario = self.cleaned_data['tipo_usuario']
                perfil.nome_empresa = self.cleaned_data.get('nome_empresa')
                perfil.save()
        return user