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

    def test_cadastra_produto_vendido_somente_por_unidade(self):
        response = self.client.post(
            self.url,
            {**self.dados_produto, "nivel_embalagem": "unidade"},
        )

        self.assertRedirects(response, self.url)
        self.assertTrue(
            Produto.objects.filter(codigo_barras_unidade="789123").exists()
        )
        self.assertEqual(UnidadeMedida.objects.count(), 0)

    def test_cadastra_produto_com_pacote_e_fardo_em_um_envio(self):
        response = self.client.post(
            self.url,
            {
                **self.dados_produto,
                "nivel_embalagem": "fardo",
                "pacote-fator_conversao": "6",
                "fardo-fator_conversao": "4",
                "pacote-codigo_barras": "111",
                "fardo-codigo_barras": "222",
            },
        )

        self.assertRedirects(response, self.url)
        produto = Produto.objects.get(codigo_barras_unidade="789123")
        pacote = UnidadeMedida.objects.get(produto=produto, tipo="PCT")
        fardo = UnidadeMedida.objects.get(produto=produto, tipo="FARDO")
        self.assertEqual(pacote.fator_conversao, 6)
        self.assertEqual(fardo.fator_conversao, 24)
        self.assertEqual(pacote.codigo_barras, "111")
        self.assertEqual(fardo.codigo_barras, "222")

    def test_nao_salva_produto_quando_pacote_obrigatorio_invalido(self):
        response = self.client.post(
            self.url,
            {**self.dados_produto, "nivel_embalagem": "pacote"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Produto.objects.filter(codigo_barras_unidade="789123").exists()
        )
        self.assertIn(
            "fator_conversao", response.context["formPacote"].errors
        )
