from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from .models import (
    Devolucao,
    ItemVenda,
    ItemVendaLote,
    LoteEstoque,
    MovimentacaoEstoque,
    Venda,
)

CASAS_CUSTO = Decimal("0.0001")
CENTAVOS = Decimal("0.01")


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


def devolver_ao_lote(lote_id, quantidade, venda, tipo):
    LoteEstoque.objects.filter(pk=lote_id).update(
        quantidade_disponivel=F("quantidade_disponivel") + quantidade
    )
    MovimentacaoEstoque.objects.create(
        lote_id=lote_id,
        venda=venda,
        tipo=tipo,
        quantidade=quantidade,
    )


@transaction.atomic
def registrar_venda(itens, desconto, forma_pagamento):
    subtotal = sum(item["valor_total"] for item in itens)
    if desconto > subtotal:
        raise ErroEstoque("O desconto não pode ser maior que o valor da venda.")

    venda = Venda.objects.create(
        forma_pagamento=forma_pagamento,
        subtotal=subtotal,
        desconto=desconto,
        total=subtotal - desconto,
    )
    for dados in itens:
        embalagem = dados.get("embalagem")
        fator = embalagem.fator_conversao if embalagem else 1
        unidades = dados["quantidade"] * fator
        item = ItemVenda.objects.create(
            venda=venda,
            produto=dados["produto"],
            embalagem_descricao=(
                f"{dados['quantidade']} x {embalagem.tipo} ({fator} un.)"
                if embalagem
                else ""
            ),
            quantidade=unidades,
            valor_total=dados["valor_total"],
        )
        for lote, retirada in consumir_lotes(dados["produto"], unidades):
            ItemVendaLote.objects.create(
                item=item,
                lote=lote,
                quantidade=retirada,
                custo_unitario=lote.preco_custo_unitario,
            )
            MovimentacaoEstoque.objects.create(
                lote=lote,
                venda=venda,
                tipo=MovimentacaoEstoque.Tipo.VENDA,
                quantidade=-retirada,
            )
    return venda


@transaction.atomic
def cancelar_venda(venda):
    venda = Venda.objects.select_for_update().get(pk=venda.pk)
    if venda.cancelada:
        raise ErroEstoque("Essa venda já foi cancelada.")
    if Devolucao.objects.filter(item__venda=venda).exists():
        raise ErroEstoque("Essa venda tem devoluções e não pode ser cancelada.")

    for vendido in ItemVendaLote.objects.filter(item__venda=venda):
        devolver_ao_lote(
            vendido.lote_id,
            vendido.quantidade,
            venda,
            MovimentacaoEstoque.Tipo.CANCELAMENTO,
        )

    venda.status = Venda.Status.CANCELADA
    venda.cancelada_em = timezone.now()
    venda.save(update_fields=["status", "cancelada_em"])


def calcular_valor_devolucao(venda, item, quantidade):
    """Divide o desconto entre os itens e evita sobra de centavos no fim."""
    unidades_restantes = sum(
        outro.quantidade_restante for outro in venda.itens.all()
    )
    if quantidade == unidades_restantes:
        return venda.total - venda.valor_devolvido

    proporcao = venda.total / venda.subtotal if venda.subtotal else Decimal("0")
    valor_item = item.valor_total * proporcao
    if quantidade == item.quantidade_restante:
        ja_devolvido = item.devolucoes.aggregate(total=Sum("valor"))["total"] or 0
        return (valor_item - ja_devolvido).quantize(CENTAVOS)
    return (valor_item * quantidade / item.quantidade).quantize(CENTAVOS)


@transaction.atomic
def registrar_devolucao(item, quantidade, voltar_ao_estoque, motivo=""):
    venda = Venda.objects.select_for_update().get(pk=item.venda_id)
    if venda.cancelada:
        raise ErroEstoque("Essa venda foi cancelada.")
    if quantidade > item.quantidade_restante:
        raise ErroEstoque(
            f"Restam apenas {item.quantidade_restante} unidades para devolver."
        )

    devolucao = Devolucao.objects.create(
        item=item,
        quantidade=quantidade,
        valor=calcular_valor_devolucao(venda, item, quantidade),
        voltou_ao_estoque=voltar_ao_estoque,
        motivo=motivo,
    )
    if not voltar_ao_estoque:
        return devolucao

    restante = quantidade
    for vendido in item.lotes.select_for_update().order_by("-pk"):
        retorno = min(restante, vendido.quantidade - vendido.quantidade_devolvida)
        if not retorno:
            continue
        vendido.quantidade_devolvida += retorno
        vendido.save(update_fields=["quantidade_devolvida"])
        devolver_ao_lote(
            vendido.lote_id,
            retorno,
            venda,
            MovimentacaoEstoque.Tipo.DEVOLUCAO,
        )
        restante -= retorno
        if not restante:
            break
    return devolucao
