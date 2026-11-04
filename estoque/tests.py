from django.contrib.auth import get_user_model
from django.test import TestCase

from django.urls import reverse

from .forms import CategoriaForm
from .models import Categoria, Produto, UnidadeMedida


class UsuarioLogadoTestCase(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user("dono", password="senha")
        self.client.force_login(self.usuario)
        self.categoria = Categoria.objects.create(nome="Alimento")


class CadastrarProdutoTests(UsuarioLogadoTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("estoque:cadastrar_produto")
        self.dados_produto = {
            "codigo_barras_unidade": "789123",
            "categoria": self.categoria.pk,
            "nome": "Arroz",
            "preco_venda_base": "7.50",
        }

    def test_pagina_exibe_botao_para_adicionar_embalagens(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadastrar embalagem")
        self.assertContains(response, "embalagens-TOTAL_FORMS")
        self.assertNotContains(response, "Pacote")
        self.assertNotContains(response, "Fardo")

    def test_cadastra_produto_vendido_somente_por_unidade(self):
        response = self.client.post(
            self.url,
            {
                **self.dados_produto,
                "embalagens-TOTAL_FORMS": "0",
                "embalagens-INITIAL_FORMS": "0",
                "embalagens-MIN_NUM_FORMS": "0",
                "embalagens-MAX_NUM_FORMS": "1000",
            },
        )

        self.assertRedirects(response, self.url)
        self.assertTrue(
            Produto.objects.filter(codigo_barras_unidade="789123").exists()
        )
        self.assertEqual(UnidadeMedida.objects.count(), 0)

    def test_cadastra_produto_com_varias_embalagens_personalizadas(self):
        response = self.client.post(
            self.url,
            {
                **self.dados_produto,
                "embalagens-TOTAL_FORMS": "2",
                "embalagens-INITIAL_FORMS": "0",
                "embalagens-MIN_NUM_FORMS": "0",
                "embalagens-MAX_NUM_FORMS": "1000",
                "embalagens-0-tipo": "Caixa",
                "embalagens-0-fator_conversao": "6",
                "embalagens-0-codigo_barras": "111",
                "embalagens-1-tipo": "Fardo grande",
                "embalagens-1-fator_conversao": "24",
                "embalagens-1-codigo_barras": "222",
            },
        )

        self.assertRedirects(response, self.url)
        produto = Produto.objects.get(codigo_barras_unidade="789123")
        caixa = UnidadeMedida.objects.get(produto=produto, tipo="Caixa")
        fardo = UnidadeMedida.objects.get(produto=produto, tipo="Fardo grande")
        self.assertEqual(caixa.fator_conversao, 6)
        self.assertEqual(fardo.fator_conversao, 24)
        self.assertEqual(caixa.codigo_barras, "111")
        self.assertEqual(fardo.codigo_barras, "222")

    def test_ignora_embalagem_removida(self):
        response = self.client.post(
            self.url,
            {
                **self.dados_produto,
                "embalagens-TOTAL_FORMS": "1",
                "embalagens-INITIAL_FORMS": "0",
                "embalagens-MIN_NUM_FORMS": "0",
                "embalagens-MAX_NUM_FORMS": "1000",
                "embalagens-0-tipo": "Caixa",
                "embalagens-0-fator_conversao": "6",
                "embalagens-0-DELETE": "on",
            },
        )

        self.assertRedirects(response, self.url)
        self.assertEqual(UnidadeMedida.objects.count(), 0)

    def test_nao_salva_produto_quando_embalagem_invalida(self):
        response = self.client.post(
            self.url,
            {
                **self.dados_produto,
                "embalagens-TOTAL_FORMS": "1",
                "embalagens-INITIAL_FORMS": "0",
                "embalagens-MIN_NUM_FORMS": "0",
                "embalagens-MAX_NUM_FORMS": "1000",
                "embalagens-0-tipo": "Caixa",
                "embalagens-0-fator_conversao": "0",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Produto.objects.filter(codigo_barras_unidade="789123").exists()
        )
        self.assertIn(
            "fator_conversao",
            response.context["formEmbalagens"].forms[0].errors,
        )

    def test_cadastra_produto_sem_codigo_de_barras(self):
        for nome in ["Brinco", "Colar"]:
            response = self.client.post(
                self.url,
                {
                    **self.dados_produto,
                    "nome": nome,
                    "codigo_barras_unidade": "",
                    "embalagens-TOTAL_FORMS": "0",
                    "embalagens-INITIAL_FORMS": "0",
                },
            )
            self.assertRedirects(response, self.url)

        self.assertEqual(
            Produto.objects.filter(codigo_barras_unidade__isnull=True).count(),
            2,
        )

    def test_exige_preco_de_venda(self):
        response = self.client.post(
            self.url,
            {
                **self.dados_produto,
                "preco_venda_base": "",
                "embalagens-TOTAL_FORMS": "0",
                "embalagens-INITIAL_FORMS": "0",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("preco_venda_base", response.context["formProduto"].errors)
        self.assertFalse(Produto.objects.exists())


class EditarProdutoTests(UsuarioLogadoTestCase):
    def setUp(self):
        super().setUp()
        self.produto = Produto.objects.create(
            nome="Arroz",
            categoria=self.categoria,
            preco_venda_base="7.50",
        )
        self.caixa = UnidadeMedida.objects.create(
            produto=self.produto,
            tipo="Caixa",
            fator_conversao=6,
        )
        self.url = reverse("estoque:editar_produto", args=[self.produto.pk])

    def dados(self, **extras):
        return {
            "nome": "Arroz integral",
            "categoria": self.categoria.pk,
            "codigo_barras_unidade": "",
            "preco_venda_base": "8.00",
            "embalagens-TOTAL_FORMS": "1",
            "embalagens-INITIAL_FORMS": "1",
            "embalagens-0-id": self.caixa.pk,
            "embalagens-0-tipo": "Caixa",
            "embalagens-0-fator_conversao": "12",
            **extras,
        }

    def test_edita_produto_e_embalagem(self):
        response = self.client.post(self.url, self.dados())

        self.assertRedirects(response, reverse("estoque:listar_produtos"))
        self.produto.refresh_from_db()
        self.caixa.refresh_from_db()
        self.assertEqual(self.produto.nome, "Arroz integral")
        self.assertEqual(self.caixa.fator_conversao, 12)

    def test_remove_embalagem_existente(self):
        self.client.post(self.url, self.dados(**{"embalagens-0-DELETE": "on"}))

        self.assertFalse(UnidadeMedida.objects.exists())


class ListarProdutosTests(UsuarioLogadoTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("estoque:listar_produtos")
        self.escola = Categoria.objects.create(nome="Escolar")
        self.biscoito = Produto.objects.create(
            nome="Biscoito",
            categoria=self.categoria,
            codigo_barras_unidade="789",
            preco_venda_base="3.00",
        )
        self.caderno = Produto.objects.create(
            nome="Caderno",
            categoria=self.escola,
            preco_venda_base="12.00",
        )
        self.brinco = Produto.objects.create(
            nome="Brinco",
            categoria=self.escola,
            preco_venda_base="9.00",
            ativo=False,
        )

    def nomes(self, **filtros):
        response = self.client.get(self.url, filtros)
        return [produto.nome for produto in response.context["pagina"]]

    def test_mostra_somente_ativos_por_padrao(self):
        self.assertEqual(self.nomes(), ["Biscoito", "Caderno"])

    def test_filtra_por_status(self):
        self.assertEqual(self.nomes(status="inativos"), ["Brinco"])
        self.assertEqual(
            self.nomes(status="todos"),
            ["Biscoito", "Brinco", "Caderno"],
        )

    def test_busca_por_nome_ou_codigo(self):
        self.assertEqual(self.nomes(busca="bisc"), ["Biscoito"])
        self.assertEqual(self.nomes(busca="789"), ["Biscoito"])

    def test_filtra_por_categoria(self):
        self.assertEqual(self.nomes(categoria=self.escola.pk), ["Caderno"])

    def test_desativa_e_reativa_produto(self):
        url = reverse("estoque:alterar_status_produto", args=[self.biscoito.pk])

        self.client.post(url)
        self.biscoito.refresh_from_db()
        self.assertFalse(self.biscoito.ativo)

        self.client.post(url)
        self.biscoito.refresh_from_db()
        self.assertTrue(self.biscoito.ativo)

    def test_status_nao_muda_com_get(self):
        url = reverse("estoque:alterar_status_produto", args=[self.biscoito.pk])

        self.assertEqual(self.client.get(url).status_code, 405)


class CategoriaTests(UsuarioLogadoTestCase):
    def test_lista_categorias_em_ordem_alfabetica(self):
        Categoria.objects.create(nome="Bijuteria")
        Categoria.objects.create(nome="Escolar")

        response = self.client.get(reverse("estoque:listar_categorias"))

        self.assertEqual(
            [categoria.nome for categoria in response.context["categorias"]],
            ["Alimento", "Bijuteria", "Escolar"],
        )

    def test_cria_categoria(self):
        url = reverse("estoque:listar_categorias")

        response = self.client.post(url, {"nome": "Bijuteria"})

        self.assertRedirects(response, url)
        self.assertTrue(Categoria.objects.filter(nome="Bijuteria").exists())

    def test_nao_aceita_nome_repetido_com_outra_caixa(self):
        form = CategoriaForm({"nome": "ALIMENTO"})

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Já existe uma categoria com esse nome.",
            form.non_field_errors(),
        )

    def test_exclui_categoria_sem_produtos(self):
        url = reverse("estoque:excluir_categoria", args=[self.categoria.pk])

        self.client.post(url)

        self.assertFalse(Categoria.objects.exists())

    def test_nao_exclui_categoria_com_produtos(self):
        Produto.objects.create(
            nome="Arroz",
            categoria=self.categoria,
            preco_venda_base="7.50",
        )
        url = reverse("estoque:excluir_categoria", args=[self.categoria.pk])

        self.client.post(url)

        self.assertTrue(Categoria.objects.filter(pk=self.categoria.pk).exists())


class AcessoTests(TestCase):
    def test_exige_login(self):
        url = reverse("estoque:listar_produtos")

        response = self.client.get(url)

        self.assertRedirects(response, f"{reverse('login')}?next={url}")

    def test_pagina_de_login_abre(self):
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
