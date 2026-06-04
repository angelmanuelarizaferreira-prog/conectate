# -*- coding: utf-8 -*-
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('emotions', '0004_chat'),
        ('accounts', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='Logro',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clave', models.CharField(max_length=40)),
                ('desbloqueado', models.DateTimeField(auto_now_add=True)),
                ('estudiante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logros', to='accounts.user')),
            ],
            options={'ordering': ['-desbloqueado']},
        ),
        migrations.AlterUniqueTogether(
            name='logro',
            unique_together={('estudiante', 'clave')},
        ),
    ]
