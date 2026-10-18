from django.urls import path
from estoque.views import cadastrarProduto
app_name = 'estoque'
urlpatterns = [
    path('itens/', cadastrarProduto, name='cadastrar_produto' )
]