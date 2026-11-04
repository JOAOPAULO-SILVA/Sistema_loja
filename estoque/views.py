from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.db.models import Count, DecimalField, ExpressionWrapper, F, OuterRef, ProtectedError, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import formats
from django.views.decorators.http import require_POST

from estoque import services
from estoque.forms import (
    AjusteEstoqueForm,
    CategoriaForm,
    DevolucaoForm,
    EntradaEstoqueForm,
    FiltroProdutosForm,
    FiltroVendasForm,
    ProdutoForm,
    UnidadeMedidaFormSet,
    VendaForm,
)
from .models import Categoria, ItemVenda, LoteEstoque, MovimentacaoEstoque, Produto, UnidadeMedida, Venda
# Create your views here.

def listarProdutos(request):
    ultimo_custo = LoteEstoque.objects.filter(
        produto=OuterRef('pk')
    ).order_by('-data_entrada', '-pk').values('preco_custo_unitario')[:1]
    produtos = Produto.objects.select_related('categoria').annotate(
        saldo=Coalesce(Sum('loteestoque__quantidade_disponivel'), 0),
        ultimo_custo=Subquery(ultimo_custo),
        lucro_unitario=ExpressionWrapper(
            F('preco_venda_base') - F('ultimo_custo'),
            output_field=DecimalField(max_digits=12, decimal_places=4),
        ),
    ).order_by('nome')
    filtro = FiltroProdutosForm(request.GET)
    dados = filtro.cleaned_data if filtro.is_valid() else {}

    busca = dados.get('busca')
    if busca:
        produtos = produtos.filter(
            Q(nome__icontains=busca) | Q(codigo_barras_unidade=busca)
        )
    if dados.get('categoria'):
        produtos = produtos.filter(categoria=dados['categoria'])

    status = dados.get('status') or 'ativos'
    if status != 'todos':
        produtos = produtos.filter(ativo=status == 'ativos')

    parametros = request.GET.copy()
    parametros.pop('page', None)
    context = {
        'pagina': Paginator(produtos, 25).get_page(request.GET.get('page')),
        'filtro': filtro,
        'parametros': parametros.urlencode(),
    }
    return render(request, 'listar_produtos.html', context)

def salvarProduto(request, produto, redirecionar_para, mensagem):
    dados = request.POST if request.method == "POST" else None
    formProduto = ProdutoForm(dados, instance=produto)
    formEmbalagens = UnidadeMedidaFormSet(
        dados,
        instance=formProduto.instance,
        prefix="embalagens",
    )

    if request.method == "POST":
        produto_valido = formProduto.is_valid()
        embalagens_validas = formEmbalagens.is_valid()

        if produto_valido and embalagens_validas:
            with transaction.atomic():
                formEmbalagens.instance = formProduto.save()
                formEmbalagens.save()

            messages.success(request, mensagem)
            return redirect(redirecionar_para)

    context = {
        'formProduto': formProduto,
        'formEmbalagens': formEmbalagens,
        'produto': produto,
    }
    return render(request, 'cadastrar_item.html', context)

def cadastrarProduto(request):
    return salvarProduto(
        request,
        None,
        "estoque:cadastrar_produto",
        "Produto cadastrado com sucesso.",
    )

def editarProduto(request, pk):
    return salvarProduto(
        request,
        get_object_or_404(Produto, pk=pk),
        "estoque:listar_produtos",
        "Produto atualizado com sucesso.",
    )

@require_POST
def alterarStatusProduto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    produto.ativo = not produto.ativo
    produto.save(update_fields=['ativo'])
    acao = "reativado" if produto.ativo else "desativado"
    messages.success(request, f"{produto.nome} foi {acao}.")
    return redirect("estoque:listar_produtos")

def estoqueProduto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    lotes = produto.loteestoque_set.annotate(
        total_movimentacoes=Count('movimentacaoestoque')
    ).filter(quantidade_disponivel__gt=0).order_by('data_entrada', 'pk')
    movimentacoes = MovimentacaoEstoque.objects.filter(
        lote__produto=produto
    ).select_related('lote')
    context = {
        'produto': produto,
        'saldo': sum(lote.quantidade_disponivel for lote in lotes),
        'lotes': lotes,
        'pagina': Paginator(movimentacoes, 25).get_page(request.GET.get('page')),
    }
    return render(request, 'estoque_produto.html', context)

def registrarEntrada(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    form = EntradaEstoqueForm(request.POST or None, produto=produto)
    if request.method == "POST" and form.is_valid():
        lote = services.registrar_entrada(
            produto,
            form.cleaned_data['quantidade'],
            form.cleaned_data['preco'],
            form.cleaned_data['embalagem'],
        )
        messages.success(
            request,
            f"Entrada de {lote.quantidade_inicial} unidades registrada.",
        )
        return redirect("estoque:estoque_produto", pk=produto.pk)

    embalagens = {
        str(embalagem.pk): embalagem.fator_conversao
        for embalagem in form.fields['embalagem'].queryset
    }
    return render(
        request,
        'registrar_entrada.html',
        {'produto': produto, 'form': form, 'embalagens': embalagens},
    )

def ajustarEstoque(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    form = AjusteEstoqueForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.ajustar_estoque(produto, **form.cleaned_data)
        except services.ErroEstoque as erro:
            form.add_error(None, str(erro))
        else:
            messages.success(request, "Ajuste registrado.")
            return redirect("estoque:estoque_produto", pk=produto.pk)

    return render(
        request,
        'ajustar_estoque.html',
        {'produto': produto, 'form': form},
    )

@require_POST
def excluirEntrada(request, pk):
    lote = get_object_or_404(LoteEstoque, pk=pk)
    try:
        services.excluir_entrada(lote)
    except services.ErroEstoque as erro:
        messages.error(request, str(erro))
    else:
        messages.success(request, "Entrada excluída.")
    return redirect("estoque:estoque_produto", pk=lote.produto_id)

def listarMovimentacoes(request):
    movimentacoes = MovimentacaoEstoque.objects.select_related('lote__produto')
    tipo = request.GET.get('tipo')
    if tipo in MovimentacaoEstoque.Tipo.values:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    else:
        tipo = ''

    context = {
        'pagina': Paginator(movimentacoes, 25).get_page(request.GET.get('page')),
        'tipos': MovimentacaoEstoque.Tipo.choices,
        'tipo': tipo,
        'parametros': f'tipo={tipo}' if tipo else '',
    }
    return render(request, 'listar_movimentacoes.html', context)

def listarVendas(request):
    vendas = Venda.objects.all()
    filtro = FiltroVendasForm(request.GET)
    filtro.is_valid()
    if filtro.cleaned_data.get('de'):
        vendas = vendas.filter(data__date__gte=filtro.cleaned_data['de'])
    if filtro.cleaned_data.get('ate'):
        vendas = vendas.filter(data__date__lte=filtro.cleaned_data['ate'])

    parametros = request.GET.copy()
    parametros.pop('page', None)
    context = {
        'pagina': Paginator(vendas, 25).get_page(request.GET.get('page')),
        'filtro': filtro,
        'parametros': parametros.urlencode(),
    }
    return render(request, 'listar_vendas.html', context)

def buscarProdutos(request):
    termo = request.GET.get('q', '').strip()
    ativos = Produto.objects.filter(ativo=True)
    embalagem = None
    if not termo:
        produtos = ativos.none()
    else:
        embalagem = UnidadeMedida.objects.filter(
            codigo_barras=termo,
            produto__ativo=True,
        ).first()
        if embalagem:
            produtos = ativos.filter(pk=embalagem.produto_id)
        else:
            produtos = ativos.filter(codigo_barras_unidade=termo)
    exato = produtos.exists()
    if termo and not exato:
        produtos = ativos.filter(nome__icontains=termo)

    produtos = produtos.annotate(
        saldo=Coalesce(Sum('loteestoque__quantidade_disponivel'), 0)
    ).order_by('nome').prefetch_related('unidademedida_set')[:10]
    resultados = [
        {
            'id': produto.pk,
            'nome': produto.nome,
            'preco': str(produto.preco_venda_base),
            'saldo': produto.saldo,
            'embalagens': [
                {
                    'id': opcao.pk,
                    'tipo': opcao.tipo,
                    'fator': opcao.fator_conversao,
                }
                for opcao in produto.unidademedida_set.all()
            ],
        }
        for produto in produtos
    ]
    return JsonResponse({
        'resultados': resultados,
        'exato': exato,
        'embalagem': embalagem.pk if embalagem else None,
    })

def novaVenda(request):
    form = VendaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            venda = services.registrar_venda(
                form.cleaned_data['itens'],
                form.cleaned_data['desconto'],
                form.cleaned_data['forma_pagamento'],
            )
        except services.ErroEstoque as erro:
            form.add_error(None, str(erro))
        else:
            messages.success(request, "Venda registrada.")
            return redirect("estoque:detalhe_venda", pk=venda.pk)

    return render(request, 'nova_venda.html', {'form': form})

def detalheVenda(request, pk):
    venda = get_object_or_404(Venda, pk=pk)
    itens = venda.itens.select_related('produto').prefetch_related('devolucoes')
    return render(
        request,
        'detalhe_venda.html',
        {'venda': venda, 'itens': itens},
    )

@require_POST
def cancelarVenda(request, pk):
    venda = get_object_or_404(Venda, pk=pk)
    try:
        services.cancelar_venda(venda)
    except services.ErroEstoque as erro:
        messages.error(request, str(erro))
    else:
        messages.success(request, "Venda cancelada e estoque restaurado.")
    return redirect("estoque:detalhe_venda", pk=venda.pk)

def devolverItem(request, pk):
    item = get_object_or_404(ItemVenda.objects.select_related('produto', 'venda'), pk=pk)
    form = DevolucaoForm(request.POST or None, initial={'quantidade': item.quantidade_restante})
    if request.method == "POST" and form.is_valid():
        try:
            devolucao = services.registrar_devolucao(
                item,
                form.cleaned_data['quantidade'],
                form.cleaned_data['voltar_ao_estoque'],
                form.cleaned_data['motivo'],
            )
        except services.ErroEstoque as erro:
            form.add_error(None, str(erro))
        else:
            messages.success(
                request,
                f"Devolução registrada: R$ {formats.localize(devolucao.valor)}.",
            )
            return redirect("estoque:detalhe_venda", pk=item.venda_id)

    return render(request, 'devolver_item.html', {'item': item, 'form': form})

def listarCategorias(request):
    form = CategoriaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Categoria criada com sucesso.")
        return redirect("estoque:listar_categorias")

    categorias = Categoria.objects.annotate(
        total_produtos=Count('produto')
    ).order_by('nome')
    return render(
        request,
        'listar_categorias.html',
        {'categorias': categorias, 'form': form},
    )

def editarCategoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    form = CategoriaForm(request.POST or None, instance=categoria)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Categoria atualizada com sucesso.")
        return redirect("estoque:listar_categorias")

    return render(
        request,
        'editar_categoria.html',
        {'categoria': categoria, 'form': form},
    )

@require_POST
def excluirCategoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    try:
        categoria.delete()
    except ProtectedError:
        messages.error(request, "Essa categoria ainda tem produtos e não pode ser excluída.")
    else:
        messages.success(request, "Categoria excluída.")
    return redirect("estoque:listar_categorias")
