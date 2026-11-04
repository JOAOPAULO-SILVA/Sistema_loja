from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='estoque:listar_produtos')),
    path('admin/', admin.site.urls),
    path('entrar/', auth_views.LoginView.as_view(redirect_authenticated_user=True), name='login'),
    path('sair/', auth_views.LogoutView.as_view(), name='logout'),
    path('estoque/', include('estoque.urls')),
]
