from django.urls import path
from estoque.views import cadastrarProduto, listarProdutos
app_name = 'estoque'
urlpatterns = [
    path('', listarProdutos, name='listar_produtos'),
    path('itens/', cadastrarProduto, name='cadastrar_produto' )
]