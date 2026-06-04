# -*- coding: utf-8 -*-
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('emotions', '0005_logros'),
        ('accounts', '0001_initial'),
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MensajeDirecto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('contenido', models.TextField()),
                ('leido', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('remitente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mensajes_enviados', to='accounts.user')),
                ('destinatario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mensajes_recibidos', to='accounts.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='PostForo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('contenido', models.TextField(max_length=500)),
                ('anonimo', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('curso', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts_foro', to='courses.curso')),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts_foro', to='accounts.user')),
                ('apoyos', models.ManyToManyField(blank=True, related_name='posts_apoyados', to='accounts.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='RutinaCierre',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('fecha', models.DateField()),
                ('salio_bien', models.TextField(verbose_name='Que salio bien hoy')),
                ('fue_dificil', models.TextField(blank=True)),
                ('manana', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('estudiante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rutinas_cierre', to='accounts.user')),
            ],
            options={'ordering': ['-fecha']},
        ),
        migrations.AlterUniqueTogether(
            name='rutinacierre',
            unique_together={('estudiante', 'fecha')},
        ),
    ]
