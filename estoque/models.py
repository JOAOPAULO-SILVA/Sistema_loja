from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class Categoria(models.Model):
    nome = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                Lower("nome"),
                name="categoria_nome_unico",
                violation_error_message="Já existe uma categoria com esse nome.",
            ),
        ]

    def __str__(self):
        return self.nome


class Produto(models.Model):
    nome = models.CharField(max_length=100)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    codigo_barras_unidade = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
    )
    preco_venda_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["nome"]

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
    embalagem = models.ForeignKey(
        UnidadeMedida,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    quantidade_embalagens = models.PositiveIntegerField(null=True, blank=True)
    preco_embalagem = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    data_entrada = models.DateTimeField(default=timezone.now, editable=False)
    preco_custo_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(0)],
    )
    quantidade_inicial = models.PositiveIntegerField()
    quantidade_disponivel = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Lote de estoque"
        verbose_name_plural = "Lotes de estoque"
        ordering = ["data_entrada", "pk"]

    def __str__(self):
        return f"{self.produto.nome} - lote {self.pk}"


class MovimentacaoEstoque(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        AJUSTE = "ajuste", "Ajuste"

    class Motivo(models.TextChoices):
        PERDA = "perda", "Perda"
        QUEBRA = "quebra", "Quebra"
        CONTAGEM = "contagem", "Contagem"
        CONSUMO = "consumo", "Consumo próprio"
        OUTRO = "outro", "Outro"

    lote = models.ForeignKey(LoteEstoque, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    quantidade = models.IntegerField()
    motivo = models.CharField(max_length=20, choices=Motivo.choices, blank=True)
    observacao = models.CharField(max_length=200, blank=True)
    data = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = "Movimentação de estoque"
        verbose_name_plural = "Movimentações de estoque"
        ordering = ["-data", "-pk"]

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.quantidade} - {self.lote}"
