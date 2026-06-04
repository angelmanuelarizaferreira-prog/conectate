# -*- coding: utf-8 -*-
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('emotions', '0003_entrada_diario'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SesionChat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(blank=True, max_length=120, verbose_name='Titulo de la sesion')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('activa', models.BooleanField(default=True)),
                ('estudiante', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sesiones_chat',
                    to='accounts.user'
                )),
            ],
            options={
                'verbose_name': 'Sesion de Chat',
                'verbose_name_plural': 'Sesiones de Chat',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='MensajeChat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rol', models.CharField(
                    max_length=10,
                    choices=[('user', 'Estudiante'), ('assistant', 'Asistente IA')]
                )),
                ('contenido', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sesion', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='mensajes',
                    to='emotions.sesionchat'
                )),
            ],
            options={
                'verbose_name': 'Mensaje de Chat',
                'verbose_name_plural': 'Mensajes de Chat',
                'ordering': ['created_at'],
            },
        ),
    ]
