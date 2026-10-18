from django import forms

from .models import LoteEstoque, Produto, UnidadeMedida


class ProdutoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.nome} ({obj.codigo_barras_unidade})"


class ProdutoForm(forms.ModelForm):
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
            "codigo_barras_unidade": "Código de barras da unidade",
            "preco_venda_base": "Preço de venda base (opcional)",
        }
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "categoria": forms.TextInput(attrs={"class": "form-control"}),
            "codigo_barras_unidade": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "preco_venda_base": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
        }


class UnidadeMedidaForm(forms.ModelForm):
    fator_conversao = forms.IntegerField(
        min_value=1,
        label="Quantidade contida",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "min": "1", "step": "1"}
        ),
    )

    class Meta:
        model = UnidadeMedida
        fields = ["fator_conversao", "codigo_barras"]
        labels = {
            "codigo_barras": "Código de barras da embalagem (opcional)",
        }
        widgets = {
            "codigo_barras": forms.TextInput(attrs={"class": "form-control"}),
        }


class LoteEstoqueForm(forms.ModelForm):
    produto = ProdutoChoiceField(
        queryset=Produto.objects.all(),
        label="Produto",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = LoteEstoque
        fields = [
            "produto",
            "preco_custo_unitario",
            "quantidade_inicial",
            "quantidade_disponivel",
        ]
        labels = {
            "preco_custo_unitario": "Custo por unidade",
            "quantidade_inicial": "Quantidade inicial em unidades",
            "quantidade_disponivel": "Quantidade disponível em unidades",
        }
        widgets = {
            "preco_custo_unitario": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "quantidade_inicial": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "step": "1"}
            ),
            "quantidade_disponivel": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "step": "1"}
            ),
        }
