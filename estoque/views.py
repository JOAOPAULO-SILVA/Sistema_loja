from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from estoque.forms import FardoForm, PacoteForm, ProdutoForm
from .models import Fardo, Pacote, Produto
# Create your views here.

def listarProdutos(request):
    produtos = Produto.objects.all()
    return render(request, 'listar_produtos.html', {'produtos': produtos})

def cadastrarProduto(request):
    nivel_embalagem = (
        request.POST.get("nivel_embalagem", "")
        if request.method == "POST"
        else "unidade"
    )
    dados = request.POST if request.method == "POST" else None
    formProduto = ProdutoForm(dados)
    formPacote = PacoteForm(dados)
    formFardo = FardoForm(dados)

    if request.method == "POST":
        nivel_valido = nivel_embalagem in {"unidade", "pacote", "fardo"}
        if not nivel_valido:
            formProduto.add_error(
                None, "Selecione se o produto será vendido em unidade, pacote ou fardo."
            )

        produto_valido = formProduto.is_valid()
        pacote_valido = nivel_embalagem == "unidade" or formPacote.is_valid()
        fardo_valido = nivel_embalagem != "fardo" or formFardo.is_valid()

        if nivel_valido and produto_valido and pacote_valido and fardo_valido:
            with transaction.atomic():
                produto = formProduto.save()
                if nivel_embalagem in {"pacote", "fardo"}:
                    pacote = formPacote.save(commit=False)
                    pacote.pct_prod = produto
                    pacote.save()
                if nivel_embalagem == "fardo":
                    fardo = formFardo.save(commit=False)
                    fardo.fardo_prod = pacote
                    fardo.save()

            messages.success(request, "Produto cadastrado com sucesso.")
            return redirect("estoque:cadastrar_produto")

    context = {
        'formProduto': formProduto,
        'formPacote': formPacote,
        'formFardo': formFardo,
        'nivel_embalagem': nivel_embalagem,
    }
    return render(request, 'cadastrar_item.html', context)