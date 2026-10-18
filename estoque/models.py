from django.db import models
from django.core.validators import MinValueValidator


class Produto(models.Model):
    prod_cod_barra = models.CharField(primary_key=True, max_length=50)
    prod_tipo = models.CharField(max_length=20)
    prod_nome = models.CharField(max_length=50)
    prod_valor_compra = models.DecimalField(max_digits=10, decimal_places=2)
    prod_valor_venda = models.DecimalField(max_digits=10, decimal_places=2)
    prod_ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"


class Pacote(models.Model):
    pct_id = models.AutoField(primary_key=True)
    pct_prod = models.ForeignKey(Produto, on_delete=models.PROTECT)
    pct_quantidade = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    pct_valor_compra = models.DecimalField(max_digits=10, decimal_places=2)
    pct_valor_venda = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Pacote"
        verbose_name_plural = "Pacotes"


class Fardo(models.Model):
    fardo_id = models.AutoField(primary_key=True)
    fardo_prod = models.ForeignKey(Pacote, on_delete=models.PROTECT)
    fardo_quantidade = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = "Fardo"
        verbose_name_plural = "Fardos"


class LoteEstoque(models.Model):
    lote_id = models.AutoField(primary_key=True)
    lote_prod = models.ForeignKey(Produto, on_delete=models.PROTECT)
    lote_validade = models.DateField(null=True, blank=True)
    lote_quantidade = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Lote de estoque"
        verbose_name_plural = "Lotes de estoque"
