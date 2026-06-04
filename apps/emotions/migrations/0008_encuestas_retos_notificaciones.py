# -*- coding: utf-8 -*-
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('emotions', '0007_nuevas_funciones'),
        ('accounts', '0001_initial'),
        ('courses', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='Encuesta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('titulo', models.CharField(max_length=150)),
                ('descripcion', models.TextField(blank=True)),
                ('tipo', models.CharField(max_length=10, choices=[('escala','Escala 1-5'),('opciones','Opciones multiple'),('texto','Respuesta libre')], default='escala')),
                ('opciones', models.JSONField(blank=True, null=True)),
                ('activa', models.BooleanField(default=True)),
                ('anonima', models.BooleanField(default=True)),
                ('fecha_limite', models.DateField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('curso', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='encuestas', to='courses.curso')),
                ('creada_por', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='encuestas_creadas', to='accounts.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='RespuestaEncuesta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('valor_escala', models.IntegerField(null=True, blank=True)),
                ('valor_opcion', models.CharField(max_length=100, blank=True)),
                ('valor_texto', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('encuesta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='respuestas_encuesta', to='emotions.encuesta')),
                ('estudiante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='respuestas_encuesta', to='accounts.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AlterUniqueTogether(name='respuestaencuesta', unique_together={('encuesta', 'estudiante')}),
        migrations.CreateModel(
            name='RetoGrupal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('titulo', models.CharField(max_length=120)),
                ('descripcion', models.TextField()),
                ('fecha_inicio', models.DateField()),
                ('fecha_fin', models.DateField()),
                ('activo', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('curso', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='retos', to='courses.curso')),
                ('creado_por', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='retos_creados', to='accounts.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Notificacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('tipo', models.CharField(max_length=15, choices=[('logro','Logro desbloqueado'),('mensaje','Nuevo mensaje'),('encuesta','Encuesta pendiente'),('reto','Nuevo reto'),('alerta','Alerta emocional'),('sistema','Sistema')])),
                ('titulo', models.CharField(max_length=120)),
                ('cuerpo', models.TextField(blank=True)),
                ('url', models.CharField(max_length=200, blank=True)),
                ('leida', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones', to='accounts.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
