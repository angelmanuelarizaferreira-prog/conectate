from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('emotions', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotaProfesor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contenido', models.TextField(verbose_name='Nota')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('profesor', models.ForeignKey(limit_choices_to={'rol__in': ['profesor', 'admin']}, on_delete=django.db.models.deletion.CASCADE, related_name='notas_escritas', to='accounts.user')),
                ('estudiante', models.ForeignKey(limit_choices_to={'rol': 'estudiante'}, on_delete=django.db.models.deletion.CASCADE, related_name='notas_recibidas', to='accounts.user')),
            ],
            options={'verbose_name': 'Nota del Profesor', 'verbose_name_plural': 'Notas del Profesor', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='MetaSemanal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('semana_inicio', models.DateField()),
                ('texto', models.CharField(max_length=200, verbose_name='Mi meta esta semana')),
                ('cumplida', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('estudiante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='metas_semanales', to='accounts.user')),
            ],
            options={'verbose_name': 'Meta Semanal', 'verbose_name_plural': 'Metas Semanales', 'ordering': ['-semana_inicio']},
        ),
        migrations.AlterUniqueTogether(
            name='metasemanal',
            unique_together={('estudiante', 'semana_inicio')},
        ),
    ]
