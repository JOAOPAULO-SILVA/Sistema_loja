from django.urls import path
from estoque.views import (
    ajustarEstoque,
    alterarStatusProduto,
    cadastrarProduto,
    editarCategoria,
    editarProduto,
    estoqueProduto,
    excluirCategoria,
    excluirEntrada,
    listarCategorias,
    listarMovimentacoes,
    listarProdutos,
    registrarEntrada,
)
app_name = 'estoque'
urlpatterns = [
    path('', listarProdutos, name='listar_produtos'),
    path('itens/', cadastrarProduto, name='cadastrar_produto'),
    path('itens/<int:pk>/editar/', editarProduto, name='editar_produto'),
    path('itens/<int:pk>/status/', alterarStatusProduto, name='alterar_status_produto'),
    path('itens/<int:pk>/estoque/', estoqueProduto, name='estoque_produto'),
    path('itens/<int:pk>/entrada/', registrarEntrada, name='registrar_entrada'),
    path('itens/<int:pk>/ajuste/', ajustarEstoque, name='ajustar_estoque'),
    path('lotes/<int:pk>/excluir/', excluirEntrada, name='excluir_entrada'),
    path('movimentacoes/', listarMovimentacoes, name='listar_movimentacoes'),
    path('categorias/', listarCategorias, name='listar_categorias'),
    path('categorias/<int:pk>/editar/', editarCategoria, name='editar_categoria'),
    path('categorias/<int:pk>/excluir/', excluirCategoria, name='excluir_categoria'),
]
