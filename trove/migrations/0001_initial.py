# Generated by Django 3.2.5 on 2023-06-29 21:31

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.expressions
import trove.models.persistent_iri


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('share', '0069_rawdatum_mediatype'),
    ]

    operations = [
        migrations.CreateModel(
            name='DerivedIndexcard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('card_as_text', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='PersistentIri',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('authorityless_scheme', models.TextField(blank=True, validators=[trove.models.persistent_iri.validate_iri_scheme_or_empty])),
                ('schemeless_iri', models.TextField()),
                ('scheme_list', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(validators=[trove.models.persistent_iri.validate_iri_scheme]), size=None)),
            ],
        ),
        migrations.CreateModel(
            name='RdfIndexcard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('card_as_turtle', models.TextField()),
                ('focus_iri', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='ThruRdfIndexcardFocusPiris',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('focus_piri', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trove.persistentiri')),
                ('rdf_indexcard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trove.rdfindexcard')),
            ],
        ),
        migrations.AddField(
            model_name='rdfindexcard',
            name='focus_piris',
            field=models.ManyToManyField(related_name='_trove_rdfindexcard_focus_piris_+', through='trove.ThruRdfIndexcardFocusPiris', to='trove.PersistentIri'),
        ),
        migrations.AddField(
            model_name='rdfindexcard',
            name='focustype_piris',
            field=models.ManyToManyField(related_name='_trove_rdfindexcard_focustype_piris_+', to='trove.PersistentIri'),
        ),
        migrations.AddField(
            model_name='rdfindexcard',
            name='from_raw_datum',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rdf_indexcard_set', to='share.rawdatum'),
        ),
        migrations.AddConstraint(
            model_name='persistentiri',
            constraint=models.CheckConstraint(check=models.Q(('scheme_list__len__gt', 0)), name='has_at_least_one_scheme'),
        ),
        migrations.AddConstraint(
            model_name='persistentiri',
            constraint=models.CheckConstraint(check=models.Q(('authorityless_scheme', ''), ('scheme_list__contains', [django.db.models.expressions.F('authorityless_scheme')]), _connector='OR'), name='authorityless_scheme__is_empty_or_known'),
        ),
        migrations.AddConstraint(
            model_name='persistentiri',
            constraint=models.CheckConstraint(check=models.Q(models.Q(('authorityless_scheme', ''), ('schemeless_iri__startswith', '//')), models.Q(models.Q(('authorityless_scheme', ''), _negated=True), models.Q(('schemeless_iri__startswith', '//'), _negated=True)), _connector='OR'), name='has_authority_or_no_need_for_one'),
        ),
        migrations.AlterUniqueTogether(
            name='persistentiri',
            unique_together={('authorityless_scheme', 'schemeless_iri')},
        ),
        migrations.AddField(
            model_name='derivedindexcard',
            name='deriver_piri',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='trove.persistentiri'),
        ),
        migrations.AddField(
            model_name='derivedindexcard',
            name='upriver_card',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trove.rdfindexcard'),
        ),
        migrations.AlterUniqueTogether(
            name='thrurdfindexcardfocuspiris',
            unique_together={('rdf_indexcard', 'focus_piri')},
        ),
        migrations.AlterUniqueTogether(
            name='derivedindexcard',
            unique_together={('upriver_card', 'deriver_piri')},
        ),
    ]
