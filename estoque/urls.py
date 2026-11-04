from django.urls import path
from estoque.views import (
    alterarStatusProduto,
    cadastrarProduto,
    editarCategoria,
    editarProduto,
    excluirCategoria,
    listarCategorias,
    listarProdutos,
)
app_name = 'estoque'
urlpatterns = [
    path('', listarProdutos, name='listar_produtos'),
    path('itens/', cadastrarProduto, name='cadastrar_produto'),
    path('itens/<int:pk>/editar/', editarProduto, name='editar_produto'),
    path('itens/<int:pk>/status/', alterarStatusProduto, name='alterar_status_produto'),
    path('categorias/', listarCategorias, name='listar_categorias'),
    path('categorias/<int:pk>/editar/', editarCategoria, name='editar_categoria'),
    path('categorias/<int:pk>/excluir/', excluirCategoria, name='excluir_categoria'),
]
