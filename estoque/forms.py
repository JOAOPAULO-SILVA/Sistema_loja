from django import forms

from .models import Fardo, LoteEstoque, Pacote, Produto


class ProdutoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.prod_nome} ({obj.prod_cod_barra})"


class PacoteChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.pct_prod.prod_nome} - pacote #{obj.pct_id} ({obj.pct_quantidade} un.)"


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = [
            "prod_cod_barra",
            "prod_tipo",
            "prod_nome",
            "prod_valor_compra",
            "prod_valor_venda",
            "prod_ativo",
        ]
        labels = {
            "prod_cod_barra": "Código de barras",
            "prod_tipo": "Tipo",
            "prod_nome": "Nome",
            "prod_valor_compra": "Valor de compra",
            "prod_valor_venda": "Valor de venda",
            "prod_ativo": "Ativo",
        }
        widgets = {
            "prod_cod_barra": forms.TextInput(attrs={"class": "form-control"}),
            "prod_tipo": forms.TextInput(attrs={"class": "form-control"}),
            "prod_nome": forms.TextInput(attrs={"class": "form-control"}),
            "prod_valor_compra": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "prod_valor_venda": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "prod_ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class PacoteForm(forms.ModelForm):
    pct_prod = ProdutoChoiceField(
        queryset=Produto.objects.all(),
        label="Produto",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    pct_quantidade = forms.IntegerField(
        min_value=1,
        label="Quantidade por pacote",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "min": "1", "step": "1"}
        ),
    )

    class Meta:
        model = Pacote
        fields = ["pct_prod", "pct_quantidade"]


class FardoForm(forms.ModelForm):
    fardo_prod = PacoteChoiceField(
        queryset=Pacote.objects.select_related("pct_prod"),
        label="Pacote",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    fardo_quantidade = forms.IntegerField(
        min_value=1,
        label="Quantidade por fardo",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "min": "1", "step": "1"}
        ),
    )

    class Meta:
        model = Fardo
        fields = ["fardo_prod", "fardo_quantidade"]


class LoteEstoqueForm(forms.ModelForm):
    lote_prod = ProdutoChoiceField(
        queryset=Produto.objects.all(),
        label="Produto",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = LoteEstoque
        fields = ["lote_prod", "lote_validade", "lote_quantidade"]
        labels = {
            "lote_validade": "Data de validade",
            "lote_quantidade": "Quantidade em estoque",
        }
        widgets = {
            "lote_validade": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "lote_quantidade": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "step": "1"}
            ),
        }