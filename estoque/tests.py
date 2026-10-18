from django.test import TestCase

from django.urls import reverse

from .models import Produto, UnidadeMedida


class CadastrarProdutoTests(TestCase):
    def setUp(self):
        self.url = reverse("estoque:cadastrar_produto")
        self.dados_produto = {
            "codigo_barras_unidade": "789123",
            "categoria": "Alimento",
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
