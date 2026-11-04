import django.core.validators
import django.db.models.deletion
import django.db.models.functions.text
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0004_alter_loteestoque_id_alter_produto_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
            ],
            options={
                'verbose_name': 'Categoria',
                'verbose_name_plural': 'Categorias',
                'ordering': ['nome'],
                'constraints': [
                    models.UniqueConstraint(
                        django.db.models.functions.text.Lower('nome'),
                        name='categoria_nome_unico',
                        violation_error_message='Já existe uma categoria com esse nome.',
                    ),
                ],
            },
        ),
        migrations.AlterModelOptions(
            name='produto',
            options={'ordering': ['nome'], 'verbose_name': 'Produto', 'verbose_name_plural': 'Produtos'},
        ),
        migrations.RemoveField(
            model_name='produto',
            name='categoria',
        ),
        migrations.AddField(
            model_name='produto',
            name='categoria',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='estoque.categoria'),
        ),
        migrations.AddField(
            model_name='produto',
            name='ativo',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='produto',
            name='codigo_barras_unidade',
            field=models.CharField(blank=True, max_length=50, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='produto',
            name='preco_venda_base',
            field=models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]
