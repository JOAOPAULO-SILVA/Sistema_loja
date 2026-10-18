from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Produto(models.Model):
    nome = models.CharField(max_length=100)
    categoria = models.CharField(max_length=100)
    codigo_barras_unidade = models.CharField(max_length=50, unique=True)
    preco_venda_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return self.nome


class UnidadeMedida(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=20)
    fator_conversao = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    codigo_barras = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Unidade de medida"
        verbose_name_plural = "Unidades de medida"

    def __str__(self):
        return f"{self.tipo} - {self.produto.nome}"


class LoteEstoque(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    data_entrada = models.DateTimeField(default=timezone.now, editable=False)
    preco_custo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    quantidade_inicial = models.PositiveIntegerField()
    quantidade_disponivel = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Lote de estoque"
        verbose_name_plural = "Lotes de estoque"

    def __str__(self):
        return f"{self.produto.nome} - lote {self.pk}"
