import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def stage_legacy_inventory(apps, schema_editor):
    Pacote = apps.get_model("estoque", "Pacote")
    Fardo = apps.get_model("estoque", "Fardo")
    LoteEstoque = apps.get_model("estoque", "LoteEstoque")
    Produto = apps.get_model("estoque", "Produto")
    LegacyUnidadeMedida = apps.get_model("estoque", "LegacyUnidadeMedida")
    LegacyLoteEstoque = apps.get_model("estoque", "LegacyLoteEstoque")

    for pacote in Pacote.objects.all():
        LegacyUnidadeMedida.objects.create(
            codigo_barras_unidade=pacote.pct_prod_id,
            tipo="PCT",
            fator_conversao=pacote.pct_quantidade,
            codigo_barras="",
        )

    for fardo in Fardo.objects.all():
        pacote = Pacote.objects.get(pk=fardo.fardo_prod_id)
        LegacyUnidadeMedida.objects.create(
            codigo_barras_unidade=pacote.pct_prod_id,
            tipo="FARDO",
            fator_conversao=pacote.pct_quantidade * fardo.fardo_quantidade,
            codigo_barras="",
        )

    now = django.utils.timezone.now()
    for lote in LoteEstoque.objects.all():
        produto = Produto.objects.get(pk=lote.lote_prod_id)
        LegacyLoteEstoque.objects.create(
            codigo_barras_unidade=produto.prod_cod_barra,
            data_entrada=now,
            preco_custo_unitario=produto.prod_valor_compra,
            quantidade_inicial=lote.lote_quantidade,
            quantidade_disponivel=lote.lote_quantidade,
        )


def copy_product_barcode(apps, schema_editor):
    Produto = apps.get_model("estoque", "Produto")
    for produto in Produto.objects.all():
        produto.codigo_barras_unidade = produto.prod_cod_barra
        produto.save(update_fields=["codigo_barras_unidade"])


def restore_inventory(apps, schema_editor):
    Produto = apps.get_model("estoque", "Produto")
    UnidadeMedida = apps.get_model("estoque", "UnidadeMedida")
    LoteEstoque = apps.get_model("estoque", "LoteEstoque")
    LegacyUnidadeMedida = apps.get_model("estoque", "LegacyUnidadeMedida")
    LegacyLoteEstoque = apps.get_model("estoque", "LegacyLoteEstoque")

    for unidade in LegacyUnidadeMedida.objects.all():
        produto = Produto.objects.get(
            codigo_barras_unidade=unidade.codigo_barras_unidade
        )
        UnidadeMedida.objects.create(
            produto=produto,
            tipo=unidade.tipo,
            fator_conversao=unidade.fator_conversao,
            codigo_barras=unidade.codigo_barras,
        )

    for lote in LegacyLoteEstoque.objects.all():
        produto = Produto.objects.get(
            codigo_barras_unidade=lote.codigo_barras_unidade
        )
        LoteEstoque.objects.create(
            produto=produto,
            data_entrada=lote.data_entrada,
            preco_custo_unitario=lote.preco_custo_unitario,
            quantidade_inicial=lote.quantidade_inicial,
            quantidade_disponivel=lote.quantidade_disponivel,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("estoque", "0002_pacote_pct_valor_compra_pacote_pct_valor_venda"),
    ]

    operations = [
        migrations.CreateModel(
            name="LegacyUnidadeMedida",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo_barras_unidade", models.CharField(max_length=50)),
                ("tipo", models.CharField(max_length=20)),
                ("fator_conversao", models.PositiveIntegerField()),
                ("codigo_barras", models.CharField(blank=True, max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name="LegacyLoteEstoque",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo_barras_unidade", models.CharField(max_length=50)),
                ("data_entrada", models.DateTimeField()),
                ("preco_custo_unitario", models.DecimalField(decimal_places=2, max_digits=10)),
                ("quantidade_inicial", models.PositiveIntegerField()),
                ("quantidade_disponivel", models.PositiveIntegerField()),
            ],
        ),
        migrations.RunPython(stage_legacy_inventory),
        migrations.DeleteModel(name="Fardo"),
        migrations.DeleteModel(name="Pacote"),
        migrations.DeleteModel(name="LoteEstoque"),
        migrations.RenameField(
            model_name="produto",
            old_name="prod_nome",
            new_name="nome",
        ),
        migrations.RenameField(
            model_name="produto",
            old_name="prod_tipo",
            new_name="categoria",
        ),
        migrations.RenameField(
            model_name="produto",
            old_name="prod_valor_venda",
            new_name="preco_venda_base",
        ),
        migrations.AlterField(
            model_name="produto",
            name="nome",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="produto",
            name="categoria",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="produto",
            name="preco_venda_base",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="produto",
            name="codigo_barras_unidade",
            field=models.CharField(
                blank=True,
                max_length=50,
                null=True,
                unique=True,
            ),
        ),
        migrations.RunPython(copy_product_barcode),
        migrations.RemoveField(
            model_name="produto",
            name="prod_cod_barra",
        ),
        migrations.AddField(
            model_name="produto",
            name="id",
            field=models.AutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name="ID",
            ),
        ),
        migrations.RemoveField(
            model_name="produto",
            name="prod_ativo",
        ),
        migrations.RemoveField(
            model_name="produto",
            name="prod_valor_compra",
        ),
        migrations.AlterField(
            model_name="produto",
            name="codigo_barras_unidade",
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.CreateModel(
            name="UnidadeMedida",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(max_length=20)),
                ("fator_conversao", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ("codigo_barras", models.CharField(blank=True, max_length=50)),
                ("produto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="estoque.produto")),
            ],
            options={
                "verbose_name": "Unidade de medida",
                "verbose_name_plural": "Unidades de medida",
            },
        ),
        migrations.CreateModel(
            name="LoteEstoque",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data_entrada", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("preco_custo_unitario", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ("quantidade_inicial", models.PositiveIntegerField()),
                ("quantidade_disponivel", models.PositiveIntegerField(default=0)),
                ("produto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="estoque.produto")),
            ],
            options={
                "verbose_name": "Lote de estoque",
                "verbose_name_plural": "Lotes de estoque",
            },
        ),
        migrations.RunPython(restore_inventory),
        migrations.DeleteModel(name="LegacyUnidadeMedida"),
        migrations.DeleteModel(name="LegacyLoteEstoque"),
    ]
