from django.shortcuts import render
from .models import Produto
# Create your views here.
def cadastrarProduto(request):
    

    return render(request, 'cadastrar_item.html', )