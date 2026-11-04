from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from estoque.forms import (
    CategoriaForm,
    FiltroProdutosForm,
    ProdutoForm,
    UnidadeMedidaFormSet,
)
from .models import Categoria, Produto
# Create your views here.

def listarProdutos(request):
    produtos = Produto.objects.select_related('categoria')
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
