from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from estoque.forms import ProdutoForm, UnidadeMedidaFormSet
from .models import Produto
# Create your views here.

def listarProdutos(request):
    produtos = Produto.objects.all()
    return render(request, 'listar_produtos.html', {'produtos': produtos})

def cadastrarProduto(request):
    dados = request.POST if request.method == "POST" else None
    formProduto = ProdutoForm(dados)
    formEmbalagens = UnidadeMedidaFormSet(dados, prefix="embalagens")

    if request.method == "POST":
        produto_valido = formProduto.is_valid()
        embalagens_validas = formEmbalagens.is_valid()

        if produto_valido and embalagens_validas:
            with transaction.atomic():
                produto = formProduto.save()
                for formEmbalagem in formEmbalagens:
                    if formEmbalagem.cleaned_data.get("DELETE"):
                        continue
                    embalagem = formEmbalagem.save(commit=False)
                    embalagem.produto = produto
                    embalagem.save()

            messages.success(request, "Produto cadastrado com sucesso.")
            return redirect("estoque:cadastrar_produto")

    context = {
        'formProduto': formProduto,
        'formEmbalagens': formEmbalagens,
    }
    return render(request, 'cadastrar_item.html', context)