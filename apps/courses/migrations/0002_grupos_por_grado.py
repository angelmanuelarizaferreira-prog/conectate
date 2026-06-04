from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('courses', '0001_initial'),
    ]
    operations = [
        # 1. Add seccion field
        migrations.AddField(
            model_name='curso',
            name='seccion',
            field=models.CharField(
                choices=[('A','A'),('B','B'),('C','C'),('D','D'),('E','E')],
                default='A', max_length=5, verbose_name='Sección',
            ),
        ),
        # 2. Migrate existing data: copy nombre → grado (first 2 chars if numeric, else '11')
        migrations.RunSQL(
            sql="""
                UPDATE courses_curso
                SET grado = CASE
                    WHEN nombre LIKE '6%' OR grado LIKE '6%' THEN '6'
                    WHEN nombre LIKE '7%' OR grado LIKE '7%' THEN '7'
                    WHEN nombre LIKE '8%' OR grado LIKE '8%' THEN '8'
                    WHEN nombre LIKE '9%' OR grado LIKE '9%' THEN '9'
                    WHEN nombre LIKE '10%' OR grado LIKE '10%' THEN '10'
                    WHEN nombre LIKE '11%' OR grado LIKE '11%' THEN '11'
                    ELSE '11'
                END;
            """,
            reverse_sql="",
        ),
        # 3. Change grado field to use choices and shorter max_length
        migrations.AlterField(
            model_name='curso',
            name='grado',
            field=models.CharField(
                choices=[
                    ('6','Grado 6'),('7','Grado 7'),('8','Grado 8'),
                    ('9','Grado 9'),('10','Grado 10'),('11','Grado 11'),
                ],
                max_length=5, verbose_name='Grado',
            ),
        ),
        # 4. Remove nombre field (now computed as property)
        migrations.RemoveField(model_name='curso', name='nombre'),
        # 5. Update verbose_name
        migrations.AlterModelOptions(
            name='curso',
            options={
                'verbose_name': 'Grupo',
                'verbose_name_plural': 'Grupos',
                'ordering': ['grado', 'seccion'],
            },
        ),
        # 6. unique_together constraint
        migrations.AlterUniqueTogether(
            name='curso',
            unique_together={('grado', 'seccion')},
        ),
    ]
