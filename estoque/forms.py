from django import forms
from django.forms import inlineformset_factory

from .models import Categoria, MovimentacaoEstoque, Produto, UnidadeMedida


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nome"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "input w-full"}),
        }


class FiltroProdutosForm(forms.Form):
    STATUS = [
        ("ativos", "Ativos"),
        ("inativos", "Inativos"),
        ("todos", "Todos"),
    ]

    busca = forms.CharField(
        required=False,
        label="Buscar",
        widget=forms.SearchInput(
            attrs={
                "class": "input w-full",
                "placeholder": "Nome ou código de barras",
            }
        ),
    )
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(),
        required=False,
        empty_label="Todas as categorias",
        widget=forms.Select(attrs={"class": "select w-full"}),
    )
    status = forms.ChoiceField(
        choices=STATUS,
        required=False,
        widget=forms.Select(attrs={"class": "select w-full"}),
    )


class ProdutoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].empty_label = "Selecione uma categoria"

    class Meta:
        model = Produto
        fields = [
            "nome",
            "categoria",
            "codigo_barras_unidade",
            "preco_venda_base",
        ]
        labels = {
            "nome": "Nome",
            "categoria": "Categoria",
            "codigo_barras_unidade": "Código de barras da unidade (opcional)",
            "preco_venda_base": "Preço de venda",
        }
        widgets = {
            "nome": forms.TextInput(attrs={"class": "input w-full"}),
            "categoria": forms.Select(attrs={"class": "select w-full"}),
            "codigo_barras_unidade": forms.TextInput(
                attrs={"class": "input w-full"}
            ),
            "preco_venda_base": forms.NumberInput(
                attrs={"class": "input w-full", "step": "0.01", "min": "0"}
            ),
        }


class UnidadeMedidaForm(forms.ModelForm):
    tipo = forms.CharField(
        max_length=20,
        label="Nome da embalagem",
        widget=forms.TextInput(attrs={"class": "input w-full"}),
    )
    fator_conversao = forms.IntegerField(
        min_value=1,
        label="Quantidade de unidades do produto",
        widget=forms.NumberInput(
            attrs={"class": "input w-full", "min": "1", "step": "1"}
        ),
    )

    class Meta:
        model = UnidadeMedida
        fields = ["tipo", "fator_conversao", "codigo_barras"]
        labels = {
            "codigo_barras": "Código de barras da embalagem (opcional)",
        }
        widgets = {
            "codigo_barras": forms.TextInput(attrs={"class": "input w-full"}),
        }


UnidadeMedidaFormSet = inlineformset_factory(
    Produto,
    UnidadeMedida,
    form=UnidadeMedidaForm,
    extra=0,
    can_delete=True,
)


class EntradaEstoqueForm(forms.Form):
    embalagem = forms.ModelChoiceField(
        queryset=UnidadeMedida.objects.none(),
        required=False,
        label="Comprado em",
        empty_label="Unidade",
        widget=forms.Select(attrs={"class": "select w-full"}),
    )
    quantidade = forms.IntegerField(
        min_value=1,
        label="Quantidade comprada",
        widget=forms.NumberInput(
            attrs={"class": "input w-full", "min": "1", "step": "1"}
        ),
    )
    preco = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=2,
        label="Valor pago por unidade ou embalagem",
        widget=forms.NumberInput(
            attrs={"class": "input w-full", "min": "0", "step": "0.01"}
        ),
    )

    def __init__(self, *args, produto, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["embalagem"].queryset = produto.unidademedida_set.all()
        self.fields["embalagem"].label_from_instance = (
            lambda embalagem: f"{embalagem.tipo} ({embalagem.fator_conversao} unidades)"
        )


class AjusteEstoqueForm(forms.Form):
    OPERACOES = [
        ("retirar", "Retirar do estoque"),
        ("acrescentar", "Acrescentar ao estoque"),
    ]

    operacao = forms.ChoiceField(
        choices=OPERACOES,
        label="Operação",
        widget=forms.Select(attrs={"class": "select w-full"}),
    )
    quantidade = forms.IntegerField(
        min_value=1,
        label="Quantidade em unidades",
        widget=forms.NumberInput(
            attrs={"class": "input w-full", "min": "1", "step": "1"}
        ),
    )
    motivo = forms.ChoiceField(
        choices=MovimentacaoEstoque.Motivo.choices,
        label="Motivo",
        widget=forms.Select(attrs={"class": "select w-full"}),
    )
    observacao = forms.CharField(
        max_length=200,
        required=False,
        label="Observação (opcional)",
        widget=forms.TextInput(attrs={"class": "input w-full"}),
    )
