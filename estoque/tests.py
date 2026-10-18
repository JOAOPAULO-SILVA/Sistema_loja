from django.test import TestCase

from django.urls import reverse

from .models import Fardo, Pacote, Produto


class CadastrarProdutoTests(TestCase):
    def setUp(self):
        self.url = reverse("estoque:cadastrar_produto")
        self.dados_produto = {
            "prod_cod_barra": "789123",
            "prod_tipo": "Alimento",
            "prod_nome": "Arroz",
            "prod_valor_compra": "5.00",
            "prod_valor_venda": "7.50",
            "prod_ativo": "on",
        }

    def test_cadastra_produto_vendido_somente_por_unidade(self):
        response = self.client.post(
            self.url,
            {**self.dados_produto, "nivel_embalagem": "unidade"},
        )

        self.assertRedirects(response, self.url)
        self.assertTrue(Produto.objects.filter(prod_cod_barra="789123").exists())
        self.assertEqual(Pacote.objects.count(), 0)
        self.assertEqual(Fardo.objects.count(), 0)

    def test_cadastra_produto_com_pacote_e_fardo_em_um_envio(self):
        response = self.client.post(
            self.url,
            {
                **self.dados_produto,
                "nivel_embalagem": "fardo",
                "pct_quantidade": "6",
                "fardo_quantidade": "4",
            },
        )

        self.assertRedirects(response, self.url)
        produto = Produto.objects.get(prod_cod_barra="789123")
        pacote = Pacote.objects.get(pct_prod=produto)
        fardo = Fardo.objects.get(fardo_prod=pacote)
        self.assertEqual(pacote.pct_quantidade, 6)
        self.assertEqual(fardo.fardo_quantidade, 4)

    def test_nao_salva_produto_quando_pacote_obrigatorio_invalido(self):
        response = self.client.post(
            self.url,
            {**self.dados_produto, "nivel_embalagem": "pacote"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Produto.objects.filter(prod_cod_barra="789123").exists())
        self.assertIn("pct_quantidade", response.context["formPacote"].errors)
