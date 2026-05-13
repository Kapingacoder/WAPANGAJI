from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0002_alter_property_options_property_description_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tenancy', '0002_maintenancerequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(choices=[('Lease Agreement', 'Lease Agreement'), ('House Rules', 'House Rules'), ('Tenant Handbook', 'Tenant Handbook'), ('Maintenance Policy', 'Maintenance Policy'), ('Payment Terms', 'Payment Terms'), ('Other', 'Other')], default='Other', max_length=50)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('file', models.FileField(upload_to='documents/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='properties.property')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documents_uploaded', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Document',
                'verbose_name_plural': 'Documents',
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
