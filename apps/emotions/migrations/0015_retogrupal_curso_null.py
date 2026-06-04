from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0003_un_grupo_por_estudiante'),
        ('emotions', '0014_remove_alerta_alerta_est_resuelta_idx_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='retogrupal',
            name='curso',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='retos',
                to='courses.curso'
            ),
        ),
    ]
