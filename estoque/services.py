from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from .models import LoteEstoque, MovimentacaoEstoque

CASAS_CUSTO = Decimal("0.0001")


class ErroEstoque(Exception):
    pass


def lotes_com_saldo(produto):
    return (
        LoteEstoque.objects.select_for_update()
        .filter(produto=produto, quantidade_disponivel__gt=0)
        .order_by("data_entrada", "pk")
    )


def saldo_produto(produto):
    saldo = LoteEstoque.objects.filter(produto=produto).aggregate(
        total=Sum("quantidade_disponivel")
    )["total"]
    return saldo or 0


def consumir_lotes(produto, quantidade):
    """Retira a quantidade dos lotes mais antigos e informa o que saiu de cada um."""
    consumo = []
    restante = quantidade
    for lote in lotes_com_saldo(produto):
        retirada = min(restante, lote.quantidade_disponivel)
        lote.quantidade_disponivel -= retirada
        lote.save(update_fields=["quantidade_disponivel"])
        consumo.append((lote, retirada))
        restante -= retirada
        if not restante:
            return consumo

    raise ErroEstoque(
        f"{produto.nome} tem apenas {quantidade - restante} em estoque."
    )


@transaction.atomic
def registrar_entrada(produto, quantidade, preco, embalagem=None):
    fator = embalagem.fator_conversao if embalagem else 1
    unidades = quantidade * fator
    lote = LoteEstoque.objects.create(
        produto=produto,
        embalagem=embalagem,
        quantidade_embalagens=quantidade if embalagem else None,
        preco_embalagem=preco if embalagem else None,
        preco_custo_unitario=(preco / fator).quantize(CASAS_CUSTO),
        quantidade_inicial=unidades,
        quantidade_disponivel=unidades,
    )
    MovimentacaoEstoque.objects.create(
        lote=lote,
        tipo=MovimentacaoEstoque.Tipo.ENTRADA,
        quantidade=unidades,
    )
    return lote


@transaction.atomic
def ajustar_estoque(produto, operacao, quantidade, motivo, observacao=""):
    if operacao == "retirar":
        movimentos = [
            (lote, -retirada)
            for lote, retirada in consumir_lotes(produto, quantidade)
        ]
    else:
        lote = (
            LoteEstoque.objects.select_for_update()
            .filter(produto=produto)
            .order_by("-data_entrada", "-pk")
            .first()
        )
        if lote is None:
            raise ErroEstoque(
                "Registre uma entrada primeiro, para o sistema saber o custo."
            )
        lote.quantidade_disponivel += quantidade
        lote.save(update_fields=["quantidade_disponivel"])
        movimentos = [(lote, quantidade)]

    for lote, movimento in movimentos:
        MovimentacaoEstoque.objects.create(
            lote=lote,
            tipo=MovimentacaoEstoque.Tipo.AJUSTE,
            quantidade=movimento,
            motivo=motivo,
            observacao=observacao,
        )


@transaction.atomic
def excluir_entrada(lote):
    lote = LoteEstoque.objects.select_for_update().get(pk=lote.pk)
    movimentacoes = lote.movimentacaoestoque_set.all()
    if movimentacoes.exclude(tipo=MovimentacaoEstoque.Tipo.ENTRADA).exists():
        raise ErroEstoque(
            "Essa entrada já teve movimentações e não pode ser excluída."
        )
    movimentacoes.delete()
    lote.delete()
