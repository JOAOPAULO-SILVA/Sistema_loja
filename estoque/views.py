from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from estoque.forms import ProdutoForm, UnidadeMedidaForm
from .models import Produto, UnidadeMedida
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
    formPacote = UnidadeMedidaForm(dados, prefix="pacote")
    formFardo = UnidadeMedidaForm(dados, prefix="fardo")
    formPacote.fields["fator_conversao"].label = "Unidades por pacote"
    formFardo.fields["fator_conversao"].label = "Pacotes por fardo"

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
                pacote = None
                if nivel_embalagem in {"pacote", "fardo"}:
                    pacote = formPacote.save(commit=False)
                    pacote.produto = produto
                    pacote.tipo = "PCT"
                    pacote.save()
                if nivel_embalagem == "fardo":
                    fardo = formFardo.save(commit=False)
                    fardo.produto = produto
                    fardo.tipo = "FARDO"
                    fardo.fator_conversao *= pacote.fator_conversao
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