# Generated by Django 5.0.7 on 2025-03-05 11:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0023_documento_archivo_rendicion_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='documento',
            name='visado_admin',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='documento',
            name='tipo',
            field=models.CharField(choices=[('FUT', 'FUT'), ('REQ', 'Requerimientos'), ('REQ-PAS', 'Requerimiento-Pasaje'), ('INF', 'Informes')], max_length=10),
        ),
        migrations.AlterField(
            model_name='memo',
            name='area_destino',
            field=models.CharField(blank=True, choices=[('SISTEMAS', 'Sistemas'), ('MARKETING', 'Marketing'), ('VENTAS', 'Ventas'), ('IMAGEN_INSTITUCIONAL', 'Imagen Institucional'), ('ACADEMICA', 'Académica'), ('TESORERIA', 'Tesorería'), ('ALMACEN', 'Almacén'), ('COORDINACION_GENERAL_FOCUS', 'Coordinación General Focus'), ('MARKETING_FOCUS', 'Área Marketing Focus'), ('PRACTICANTE', 'Practicante'), ('GERENCIA', 'Gerencia'), ('OPERATIVA', 'Operativa'), ('SIN_AREA', 'Sin Área')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='rolesusuario',
            name='area',
            field=models.CharField(choices=[('SISTEMAS', 'Sistemas'), ('MARKETING', 'Marketing'), ('VENTAS', 'Ventas'), ('IMAGEN_INSTITUCIONAL', 'Imagen Institucional'), ('ACADEMICA', 'Académica'), ('TESORERIA', 'Tesorería'), ('ALMACEN', 'Almacén'), ('COORDINACION_GENERAL_FOCUS', 'Coordinación General Focus'), ('MARKETING_FOCUS', 'Área Marketing Focus'), ('PRACTICANTE', 'Practicante'), ('GERENCIA', 'Gerencia'), ('OPERATIVA', 'Operativa'), ('SIN_AREA', 'Sin Área')], default='SISTEMAS', max_length=50),
        ),
        migrations.AlterField(
            model_name='rolesusuario',
            name='rol',
            field=models.CharField(choices=[('ADMIN', 'Admin'), ('SECRETARIA', 'Secretaria'), ('USUARIO', 'Usuario'), ('TESORERIA', 'Tesorería'), ('GERENTE', 'Gerente')], default='USUARIO', max_length=10),
        ),
    ]
