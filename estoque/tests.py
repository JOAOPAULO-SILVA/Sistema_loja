import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django.urls import reverse

from . import services
from .forms import CategoriaForm
from .models import (
    Categoria,
    Devolucao,
    ItemVenda,
    LoteEstoque,
    MovimentacaoEstoque,
    Produto,
    UnidadeMedida,
    Venda,
)


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


class EstoqueTestCase(UsuarioLogadoTestCase):
    def setUp(self):
        super().setUp()
        self.produto = Produto.objects.create(
            nome="Biscoito",
            categoria=self.categoria,
            preco_venda_base="3.00",
        )
        self.caixa = UnidadeMedida.objects.create(
            produto=self.produto,
            tipo="Caixa",
            fator_conversao=30,
        )

    def saldos(self):
        return list(
            LoteEstoque.objects.order_by("pk").values_list(
                "quantidade_disponivel", flat=True
            )
        )


class EntradaEstoqueTests(EstoqueTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("estoque:registrar_entrada", args=[self.produto.pk])

    def test_entrada_por_embalagem_calcula_unidades_e_custo(self):
        response = self.client.post(
            self.url,
            {"embalagem": self.caixa.pk, "quantidade": 2, "preco": "45.00"},
        )

        self.assertRedirects(
            response,
            reverse("estoque:estoque_produto", args=[self.produto.pk]),
        )
        lote = LoteEstoque.objects.get()
        self.assertEqual(lote.quantidade_inicial, 60)
        self.assertEqual(lote.quantidade_disponivel, 60)
        self.assertEqual(lote.preco_custo_unitario, Decimal("1.5000"))
        self.assertEqual(lote.embalagem, self.caixa)
        movimentacao = MovimentacaoEstoque.objects.get()
        self.assertEqual(movimentacao.tipo, MovimentacaoEstoque.Tipo.ENTRADA)
        self.assertEqual(movimentacao.quantidade, 60)

    def test_entrada_por_unidade(self):
        self.client.post(self.url, {"quantidade": 10, "preco": "2.00"})

        lote = LoteEstoque.objects.get()
        self.assertEqual(lote.quantidade_disponivel, 10)
        self.assertEqual(lote.preco_custo_unitario, Decimal("2.0000"))
        self.assertIsNone(lote.embalagem)

    def test_custo_guarda_quatro_casas(self):
        tres = UnidadeMedida.objects.create(
            produto=self.produto,
            tipo="Trio",
            fator_conversao=3,
        )

        self.client.post(
            self.url,
            {"embalagem": tres.pk, "quantidade": 1, "preco": "10.00"},
        )

        self.assertEqual(
            LoteEstoque.objects.get().preco_custo_unitario,
            Decimal("3.3333"),
        )

    def test_recusa_embalagem_de_outro_produto(self):
        outro = Produto.objects.create(
            nome="Caderno",
            categoria=self.categoria,
            preco_venda_base="9.00",
        )
        embalagem = UnidadeMedida.objects.create(
            produto=outro,
            tipo="Pacote",
            fator_conversao=5,
        )

        response = self.client.post(
            self.url,
            {"embalagem": embalagem.pk, "quantidade": 1, "preco": "10.00"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(LoteEstoque.objects.exists())

    def test_remover_embalagem_preserva_o_lote(self):
        services.registrar_entrada(self.produto, 1, Decimal("30.00"), self.caixa)

        self.caixa.delete()

        lote = LoteEstoque.objects.get()
        self.assertIsNone(lote.embalagem)
        self.assertEqual(lote.quantidade_disponivel, 30)

    def test_exclui_entrada_sem_movimentacoes(self):
        lote = services.registrar_entrada(self.produto, 5, Decimal("1.00"))

        self.client.post(reverse("estoque:excluir_entrada", args=[lote.pk]))

        self.assertFalse(LoteEstoque.objects.exists())
        self.assertFalse(MovimentacaoEstoque.objects.exists())

    def test_nao_exclui_entrada_movimentada(self):
        lote = services.registrar_entrada(self.produto, 5, Decimal("1.00"))
        services.ajustar_estoque(self.produto, "retirar", 1, "perda")

        self.client.post(reverse("estoque:excluir_entrada", args=[lote.pk]))

        self.assertTrue(LoteEstoque.objects.filter(pk=lote.pk).exists())


class AjusteEstoqueTests(EstoqueTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("estoque:ajustar_estoque", args=[self.produto.pk])

    def dados(self, operacao, quantidade):
        return {
            "operacao": operacao,
            "quantidade": quantidade,
            "motivo": "perda",
            "observacao": "Molhou",
        }

    def test_retirada_consome_lote_mais_antigo_primeiro(self):
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))
        services.registrar_entrada(self.produto, 5, Decimal("2.00"))

        self.client.post(self.url, self.dados("retirar", 7))

        self.assertEqual(self.saldos(), [0, 3])
        self.assertEqual(
            sorted(
                MovimentacaoEstoque.objects.filter(
                    tipo=MovimentacaoEstoque.Tipo.AJUSTE
                ).values_list("quantidade", flat=True)
            ),
            [-5, -2],
        )

    def test_nao_retira_mais_que_o_saldo(self):
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))

        response = self.client.post(self.url, self.dados("retirar", 6))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "apenas 5 em estoque")
        self.assertEqual(self.saldos(), [5])

    def test_acrescimo_vai_para_o_lote_mais_recente(self):
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))
        services.registrar_entrada(self.produto, 5, Decimal("2.00"))

        self.client.post(self.url, self.dados("acrescentar", 2))

        self.assertEqual(self.saldos(), [5, 7])

    def test_acrescimo_sem_lote_pede_entrada(self):
        response = self.client.post(self.url, self.dados("acrescentar", 2))

        self.assertContains(response, "Registre uma entrada primeiro")
        self.assertFalse(MovimentacaoEstoque.objects.exists())


class TelasEstoqueTests(EstoqueTestCase):
    def test_lista_mostra_saldo_custo_e_lucro(self):
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))
        services.registrar_entrada(self.produto, 5, Decimal("2.00"))

        response = self.client.get(reverse("estoque:listar_produtos"))

        produto = response.context["pagina"][0]
        self.assertEqual(produto.saldo, 10)
        self.assertEqual(produto.ultimo_custo, Decimal("2.0000"))
        self.assertEqual(produto.lucro_unitario, Decimal("1.0000"))

    def test_lista_produto_sem_estoque(self):
        response = self.client.get(reverse("estoque:listar_produtos"))

        produto = response.context["pagina"][0]
        self.assertEqual(produto.saldo, 0)
        self.assertIsNone(produto.lucro_unitario)

    def test_pagina_do_produto_mostra_saldo_e_historico(self):
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))
        services.ajustar_estoque(self.produto, "retirar", 2, "quebra")

        response = self.client.get(
            reverse("estoque:estoque_produto", args=[self.produto.pk])
        )

        self.assertEqual(response.context["saldo"], 3)
        self.assertEqual(len(response.context["pagina"]), 2)
        self.assertContains(response, "Quebra")

    def test_filtra_movimentacoes_por_tipo(self):
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))
        services.ajustar_estoque(self.produto, "retirar", 2, "quebra")

        response = self.client.get(
            reverse("estoque:listar_movimentacoes"),
            {"tipo": "ajuste"},
        )

        self.assertEqual(len(response.context["pagina"]), 1)


class VendaTestCase(EstoqueTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("estoque:nova_venda")

    def vender(self, *itens, desconto=None, forma="dinheiro"):
        return self.client.post(
            self.url,
            {
                "itens": json.dumps(list(itens)),
                "desconto": desconto or "",
                "forma_pagamento": forma,
            },
        )

    def item(self, quantidade, valor, embalagem=None, produto=None):
        return {
            "produto": (produto or self.produto).pk,
            "embalagem": embalagem.pk if embalagem else None,
            "quantidade": quantidade,
            "valor_total": valor,
        }


class RegistrarVendaTests(VendaTestCase):
    def test_venda_baixa_lotes_antigos_e_calcula_lucro(self):
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))
        services.registrar_entrada(self.produto, 5, Decimal("2.00"))

        response = self.vender(self.item(7, "21.00"))

        venda = Venda.objects.get()
        self.assertRedirects(
            response,
            reverse("estoque:detalhe_venda", args=[venda.pk]),
        )
        self.assertEqual(self.saldos(), [0, 3])
        self.assertEqual(venda.total, Decimal("21.00"))
        self.assertEqual(venda.custo, Decimal("9.0000"))
        self.assertEqual(venda.lucro, Decimal("12.0000"))
        self.assertEqual(
            MovimentacaoEstoque.objects.filter(
                tipo=MovimentacaoEstoque.Tipo.VENDA,
                venda=venda,
            ).count(),
            2,
        )

    def test_mudar_preco_e_custo_nao_altera_venda_antiga(self):
        lote = services.registrar_entrada(self.produto, 5, Decimal("1.00"))
        self.vender(self.item(2, "6.00"))

        LoteEstoque.objects.filter(pk=lote.pk).update(preco_custo_unitario="9.00")
        Produto.objects.filter(pk=self.produto.pk).update(preco_venda_base="99.00")

        venda = Venda.objects.get()
        self.assertEqual(venda.custo, Decimal("2.0000"))
        self.assertEqual(venda.lucro, Decimal("4.0000"))

    def test_pacote_vendido_com_preco_combinado(self):
        services.registrar_entrada(self.produto, 40, Decimal("1.00"))

        self.vender(self.item(1, "40.00", embalagem=self.caixa))

        item = ItemVenda.objects.get()
        self.assertEqual(item.quantidade, 30)
        self.assertEqual(item.valor_total, Decimal("40.00"))
        self.assertEqual(item.embalagem_descricao, "1 x Caixa (30 un.)")
        self.assertEqual(self.saldos(), [10])
        self.assertEqual(Venda.objects.get().lucro, Decimal("10.0000"))

    def test_desconto_reduz_total_e_lucro(self):
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))

        self.vender(self.item(2, "6.00"), desconto="1.00")

        venda = Venda.objects.get()
        self.assertEqual(venda.total, Decimal("5.00"))
        self.assertEqual(venda.lucro, Decimal("3.0000"))

    def test_recusa_desconto_maior_que_a_venda(self):
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))

        response = self.vender(self.item(1, "3.00"), desconto="4.00")

        self.assertContains(response, "desconto não pode ser maior")
        self.assertFalse(Venda.objects.exists())
        self.assertEqual(self.saldos(), [5])

    def test_estoque_insuficiente_nao_grava_nada(self):
        outro = Produto.objects.create(
            nome="Caderno",
            categoria=self.categoria,
            preco_venda_base="9.00",
        )
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))
        services.registrar_entrada(outro, 1, Decimal("4.00"))

        response = self.vender(
            self.item(5, "15.00"),
            self.item(2, "18.00", produto=outro),
        )

        self.assertContains(response, "Caderno tem apenas 1 em estoque")
        self.assertFalse(Venda.objects.exists())
        self.assertEqual(self.saldos(), [5, 1])

    def test_erro_mantem_itens_no_carrinho(self):
        itens = [self.item(1, "3.00") | {"nome": "Biscoito", "fator": 1}]

        response = self.vender(*itens)

        self.assertEqual(json.loads(response.context["form"]["itens"].value()), itens)

    def test_recusa_venda_vazia(self):
        response = self.vender()

        self.assertContains(response, "Adicione ao menos um produto")

    def test_recusa_itens_malformados(self):
        for itens in ["nao e json", "{}", "[1]", '[{"produto": 999}]']:
            response = self.client.post(
                self.url,
                {"itens": itens, "forma_pagamento": "pix"},
            )
            self.assertEqual(response.status_code, 200)

        self.assertFalse(Venda.objects.exists())

    def test_recusa_produto_inativo(self):
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))
        Produto.objects.update(ativo=False)

        response = self.vender(self.item(1, "3.00"))

        self.assertContains(response, "Revise os itens da venda")
        self.assertFalse(Venda.objects.exists())

    def test_recusa_embalagem_de_outro_produto(self):
        outro = Produto.objects.create(
            nome="Caderno",
            categoria=self.categoria,
            preco_venda_base="9.00",
        )
        services.registrar_entrada(outro, 50, Decimal("1.00"))

        response = self.vender(self.item(1, "3.00", self.caixa, outro))

        self.assertContains(response, "Revise os itens da venda")
        self.assertFalse(Venda.objects.exists())


class CancelarVendaTests(VendaTestCase):
    def setUp(self):
        super().setUp()
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))
        services.registrar_entrada(self.produto, 5, Decimal("2.00"))
        self.vender(self.item(7, "21.00"))
        self.venda = Venda.objects.get()
        self.url_cancelar = reverse("estoque:cancelar_venda", args=[self.venda.pk])

    def test_cancelamento_devolve_cada_lote_e_zera_resultado(self):
        self.client.post(self.url_cancelar)

        self.venda.refresh_from_db()
        self.assertTrue(self.venda.cancelada)
        self.assertIsNotNone(self.venda.cancelada_em)
        self.assertEqual(self.saldos(), [5, 5])
        self.assertEqual(self.venda.receita, 0)
        self.assertEqual(self.venda.custo, 0)

    def test_nao_cancela_duas_vezes(self):
        self.client.post(self.url_cancelar)
        self.client.post(self.url_cancelar)

        self.assertEqual(self.saldos(), [5, 5])

    def test_nao_cancela_venda_com_devolucao(self):
        services.registrar_devolucao(self.venda.itens.get(), 1, True)

        self.client.post(self.url_cancelar)

        self.venda.refresh_from_db()
        self.assertFalse(self.venda.cancelada)


class DevolucaoTests(VendaTestCase):
    def setUp(self):
        super().setUp()
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))
        services.registrar_entrada(self.produto, 5, Decimal("2.00"))

    def vender_e_obter(self, *itens, desconto=None):
        self.vender(*itens, desconto=desconto)
        return Venda.objects.get()

    def test_devolucao_parcial_volta_ao_lote_de_origem(self):
        venda = self.vender_e_obter(self.item(7, "21.00"))

        self.client.post(
            reverse("estoque:devolver_item", args=[venda.itens.get().pk]),
            {"quantidade": 3, "voltar_ao_estoque": "on"},
        )

        self.assertEqual(Devolucao.objects.get().valor, Decimal("9.00"))
        self.assertEqual(self.saldos(), [1, 5])
        self.assertEqual(venda.receita, Decimal("12.00"))
        self.assertEqual(venda.custo, Decimal("4.0000"))
        self.assertEqual(venda.lucro, Decimal("8.0000"))

    def test_produto_com_defeito_nao_volta_e_custo_continua(self):
        venda = self.vender_e_obter(self.item(2, "6.00"))

        self.client.post(
            reverse("estoque:devolver_item", args=[venda.itens.get().pk]),
            {"quantidade": 1},
        )

        self.assertEqual(self.saldos(), [3, 5])
        self.assertEqual(venda.receita, Decimal("3.00"))
        self.assertEqual(venda.custo, Decimal("2.0000"))
        self.assertEqual(venda.lucro, Decimal("1.0000"))

    def test_desconto_e_proporcional_na_devolucao(self):
        venda = self.vender_e_obter(self.item(2, "10.00"), desconto="1.00")

        devolucao = services.registrar_devolucao(venda.itens.get(), 1, True)

        self.assertEqual(devolucao.valor, Decimal("4.50"))

    def test_devolver_tudo_em_partes_zera_sem_sobrar_centavo(self):
        venda = self.vender_e_obter(self.item(3, "10.00"), desconto="0.01")
        item = venda.itens.get()

        for _ in range(3):
            services.registrar_devolucao(item, 1, True)

        self.assertEqual(venda.receita, 0)
        self.assertEqual(venda.custo, 0)
        self.assertEqual(self.saldos(), [5, 5])

    def test_nao_devolve_mais_que_o_vendido(self):
        venda = self.vender_e_obter(self.item(2, "6.00"))

        response = self.client.post(
            reverse("estoque:devolver_item", args=[venda.itens.get().pk]),
            {"quantidade": 3, "voltar_ao_estoque": "on"},
        )

        self.assertContains(response, "Restam apenas 2 unidades")
        self.assertFalse(Devolucao.objects.exists())

    def test_nao_devolve_venda_cancelada(self):
        venda = self.vender_e_obter(self.item(2, "6.00"))
        services.cancelar_venda(venda)

        response = self.client.post(
            reverse("estoque:devolver_item", args=[venda.itens.get().pk]),
            {"quantidade": 1, "voltar_ao_estoque": "on"},
        )

        self.assertContains(response, "Essa venda foi cancelada")
        self.assertEqual(self.saldos(), [5, 5])


class BuscaEListaVendasTests(VendaTestCase):
    def buscar(self, termo):
        return self.client.get(
            reverse("estoque:buscar_produtos"),
            {"q": termo},
        ).json()

    def test_busca_por_nome(self):
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))

        dados = self.buscar("bisc")

        self.assertFalse(dados["exato"])
        self.assertEqual(dados["resultados"][0]["saldo"], 5)
        self.assertEqual(dados["resultados"][0]["embalagens"][0]["fator"], 30)

    def test_codigo_da_unidade_e_exato(self):
        Produto.objects.update(codigo_barras_unidade="789")

        dados = self.buscar("789")

        self.assertTrue(dados["exato"])
        self.assertIsNone(dados["embalagem"])

    def test_codigo_da_embalagem_indica_a_embalagem(self):
        UnidadeMedida.objects.update(codigo_barras="111")

        dados = self.buscar("111")

        self.assertTrue(dados["exato"])
        self.assertEqual(dados["embalagem"], self.caixa.pk)

    def test_busca_ignora_inativos(self):
        Produto.objects.update(ativo=False)

        self.assertEqual(self.buscar("bisc")["resultados"], [])

    def test_lista_filtra_por_data(self):
        services.registrar_entrada(self.produto, 5, Decimal("1.00"))
        self.vender(self.item(1, "3.00"))
        url = reverse("estoque:listar_vendas")

        self.assertEqual(len(self.client.get(url).context["pagina"]), 1)
        self.assertEqual(
            len(self.client.get(url, {"de": "2999-01-01"}).context["pagina"]),
            0,
        )

    def test_data_invalida_e_ignorada(self):
        response = self.client.get(
            reverse("estoque:listar_vendas"),
            {"de": "2026-13-45"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["pagina"]), 0)

    def test_excluir_entrada_vendida_e_bloqueado(self):
        lote = services.registrar_entrada(self.produto, 5, Decimal("1.00"))
        self.vender(self.item(1, "3.00"))

        self.client.post(reverse("estoque:excluir_entrada", args=[lote.pk]))

        self.assertTrue(LoteEstoque.objects.filter(pk=lote.pk).exists())


class AcessoTests(TestCase):
    def test_exige_login(self):
        url = reverse("estoque:listar_produtos")

        response = self.client.get(url)

        self.assertRedirects(response, f"{reverse('login')}?next={url}")

    def test_pagina_de_login_abre(self):
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
