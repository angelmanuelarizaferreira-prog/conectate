# -*- coding: utf-8 -*-
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('emotions', '0002_nota_meta'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EntradaDiario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(blank=True, max_length=150, verbose_name='Titulo')),
                ('contenido', models.TextField(verbose_name='Contenido')),
                ('emocion_del_dia', models.CharField(
                    blank=True, max_length=20,
                    choices=[('feliz','Feliz'),('tranquilo','Tranquilo'),('estresado','Estresado'),('triste','Triste'),('enojado','Enojado')],
                    verbose_name='Como me siento al escribir esto'
                )),
                ('estado', models.CharField(
                    max_length=10,
                    choices=[('borrador','Borrador'),('guardado','Guardado')],
                    default='guardado'
                )),
                ('es_privado', models.BooleanField(default=True, verbose_name='Solo yo puedo verlo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('estudiante', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='entradas_diario',
                    to='accounts.user'
                )),
            ],
            options={
                'verbose_name': 'Entrada de Diario',
                'verbose_name_plural': 'Entradas de Diario',
                'ordering': ['-created_at'],
            },
        ),
    ]
