from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Sum
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
        VENDA = "venda", "Venda"
        CANCELAMENTO = "cancelamento", "Cancelamento"
        DEVOLUCAO = "devolucao", "Devolução"

    class Motivo(models.TextChoices):
        PERDA = "perda", "Perda"
        QUEBRA = "quebra", "Quebra"
        CONTAGEM = "contagem", "Contagem"
        CONSUMO = "consumo", "Consumo próprio"
        OUTRO = "outro", "Outro"

    lote = models.ForeignKey(LoteEstoque, on_delete=models.PROTECT)
    venda = models.ForeignKey(
        "Venda",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
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


class Venda(models.Model):
    class FormaPagamento(models.TextChoices):
        DINHEIRO = "dinheiro", "Dinheiro"
        PIX = "pix", "Pix"
        DEBITO = "debito", "Cartão de débito"
        CREDITO = "credito", "Cartão de crédito"

    class Status(models.TextChoices):
        CONCLUIDA = "concluida", "Concluída"
        CANCELADA = "cancelada", "Cancelada"

    data = models.DateTimeField(default=timezone.now, editable=False)
    forma_pagamento = models.CharField(
        max_length=20,
        choices=FormaPagamento.choices,
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    desconto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONCLUIDA,
    )
    cancelada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Venda"
        verbose_name_plural = "Vendas"
        ordering = ["-data", "-pk"]

    def __str__(self):
        return f"Venda {self.pk}"

    @property
    def cancelada(self):
        return self.status == self.Status.CANCELADA

    @property
    def valor_devolvido(self):
        return Devolucao.objects.filter(item__venda=self).aggregate(
            total=Sum("valor")
        )["total"] or Decimal("0")

    @property
    def receita(self):
        if self.cancelada:
            return Decimal("0")
        return self.total - self.valor_devolvido

    @property
    def custo(self):
        if self.cancelada:
            return Decimal("0")
        return ItemVendaLote.objects.filter(item__venda=self).aggregate(
            total=Sum(
                (F("quantidade") - F("quantidade_devolvida")) * F("custo_unitario")
            )
        )["total"] or Decimal("0")

    @property
    def lucro(self):
        return self.receita - self.custo


class ItemVenda(models.Model):
    venda = models.ForeignKey(
        Venda,
        on_delete=models.PROTECT,
        related_name="itens",
    )
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    embalagem_descricao = models.CharField(max_length=60, blank=True)
    quantidade = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    valor_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = "Item de venda"
        verbose_name_plural = "Itens de venda"
        ordering = ["pk"]

    def __str__(self):
        return f"{self.quantidade} x {self.produto.nome}"

    @property
    def quantidade_devolvida(self):
        return self.devolucoes.aggregate(total=Sum("quantidade"))["total"] or 0

    @property
    def quantidade_restante(self):
        return self.quantidade - self.quantidade_devolvida


class ItemVendaLote(models.Model):
    item = models.ForeignKey(
        ItemVenda,
        on_delete=models.PROTECT,
        related_name="lotes",
    )
    lote = models.ForeignKey(LoteEstoque, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField()
    custo_unitario = models.DecimalField(max_digits=12, decimal_places=4)
    quantidade_devolvida = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Lote de item vendido"
        verbose_name_plural = "Lotes de itens vendidos"
        ordering = ["pk"]

    def __str__(self):
        return f"{self.item} - lote {self.lote_id}"


class Devolucao(models.Model):
    item = models.ForeignKey(
        ItemVenda,
        on_delete=models.PROTECT,
        related_name="devolucoes",
    )
    quantidade = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    voltou_ao_estoque = models.BooleanField(default=True)
    motivo = models.CharField(max_length=200, blank=True)
    data = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = "Devolução"
        verbose_name_plural = "Devoluções"
        ordering = ["pk"]

    def __str__(self):
        return f"Devolução de {self.quantidade} - {self.item.produto.nome}"
