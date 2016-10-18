# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-10-17 14:18
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('share', '0002_create_share_user'),
        ('share', '0002_create_share_user'),
    ]

    operations = [
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_extradata_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_extradataversion(persistent_id, action, change_id, data, date_created, date_modified, same_as_id, same_as_version_id) VALUES (NEW.id, TG_OP, NEW.change_id, NEW.data, NEW.date_created, NEW.date_modified, NEW.same_as_id, NEW.same_as_version_id) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_extradata_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_extradata_change ON share_extradata;\n\n        CREATE TRIGGER share_extradata_change\n        BEFORE INSERT OR UPDATE ON share_extradata\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_extradata_change();',
            reverse_sql='DROP TRIGGER share_extradata_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_venue_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_venueversion(persistent_id, action, change_id, community_identifier, date_created, date_modified, extra_id, extra_version_id, location, name, same_as_id, same_as_version_id, venue_type) VALUES (NEW.id, TG_OP, NEW.change_id, NEW.community_identifier, NEW.date_created, NEW.date_modified, NEW.extra_id, NEW.extra_version_id, NEW.location, NEW.name, NEW.same_as_id, NEW.same_as_version_id, NEW.venue_type) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_venue_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_venue_change ON share_venue;\n\n        CREATE TRIGGER share_venue_change\n        BEFORE INSERT OR UPDATE ON share_venue\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_venue_change();',
            reverse_sql='DROP TRIGGER share_venue_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_tag_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_tagversion(persistent_id, action, change_id, date_created, date_modified, extra_id, extra_version_id, name, same_as_id, same_as_version_id) VALUES (NEW.id, TG_OP, NEW.change_id, NEW.date_created, NEW.date_modified, NEW.extra_id, NEW.extra_version_id, NEW.name, NEW.same_as_id, NEW.same_as_version_id) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_tag_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_tag_change ON share_tag;\n\n        CREATE TRIGGER share_tag_change\n        BEFORE INSERT OR UPDATE ON share_tag\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_tag_change();',
            reverse_sql='DROP TRIGGER share_tag_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_throughvenues_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_throughvenuesversion(persistent_id, action, change_id, creative_work_id, creative_work_version_id, date_created, date_modified, extra_id, extra_version_id, same_as_id, same_as_version_id, venue_id, venue_version_id) VALUES (NEW.id, TG_OP, NEW.change_id, NEW.creative_work_id, NEW.creative_work_version_id, NEW.date_created, NEW.date_modified, NEW.extra_id, NEW.extra_version_id, NEW.same_as_id, NEW.same_as_version_id, NEW.venue_id, NEW.venue_version_id) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_throughvenues_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_throughvenues_change ON share_throughvenues;\n\n        CREATE TRIGGER share_throughvenues_change\n        BEFORE INSERT OR UPDATE ON share_throughvenues\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_throughvenues_change();',
            reverse_sql='DROP TRIGGER share_throughvenues_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_throughtags_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_throughtagsversion(persistent_id, action, change_id, creative_work_id, creative_work_version_id, date_created, date_modified, extra_id, extra_version_id, same_as_id, same_as_version_id, tag_id, tag_version_id) VALUES (NEW.id, TG_OP, NEW.change_id, NEW.creative_work_id, NEW.creative_work_version_id, NEW.date_created, NEW.date_modified, NEW.extra_id, NEW.extra_version_id, NEW.same_as_id, NEW.same_as_version_id, NEW.tag_id, NEW.tag_version_id) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_throughtags_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_throughtags_change ON share_throughtags;\n\n        CREATE TRIGGER share_throughtags_change\n        BEFORE INSERT OR UPDATE ON share_throughtags\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_throughtags_change();',
            reverse_sql='DROP TRIGGER share_throughtags_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_throughsubjects_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_throughsubjectsversion(persistent_id, action, change_id, creative_work_id, creative_work_version_id, date_created, date_modified, extra_id, extra_version_id, same_as_id, same_as_version_id, subject_id) VALUES (NEW.id, TG_OP, NEW.change_id, NEW.creative_work_id, NEW.creative_work_version_id, NEW.date_created, NEW.date_modified, NEW.extra_id, NEW.extra_version_id, NEW.same_as_id, NEW.same_as_version_id, NEW.subject_id) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_throughsubjects_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_throughsubjects_change ON share_throughsubjects;\n\n        CREATE TRIGGER share_throughsubjects_change\n        BEFORE INSERT OR UPDATE ON share_throughsubjects\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_throughsubjects_change();',
            reverse_sql='DROP TRIGGER share_throughsubjects_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_abstractagent_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_abstractagentversion(persistent_id, action, additional_name, change_id, date_created, date_modified, extra_id, extra_version_id, family_name, given_name, location, name, same_as_id, same_as_version_id, suffix, type) VALUES (NEW.id, TG_OP, NEW.additional_name, NEW.change_id, NEW.date_created, NEW.date_modified, NEW.extra_id, NEW.extra_version_id, NEW.family_name, NEW.given_name, NEW.location, NEW.name, NEW.same_as_id, NEW.same_as_version_id, NEW.suffix, NEW.type) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_abstractagent_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_abstractagent_change ON share_abstractagent;\n\n        CREATE TRIGGER share_abstractagent_change\n        BEFORE INSERT OR UPDATE ON share_abstractagent\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_abstractagent_change();',
            reverse_sql='DROP TRIGGER share_abstractagent_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_abstractcreativework_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_abstractcreativeworkversion(persistent_id, action, change_id, date_created, date_modified, date_published, date_updated, description, extra_id, extra_version_id, free_to_read_date, free_to_read_type, is_deleted, language, rights, same_as_id, same_as_version_id, title, type) VALUES (NEW.id, TG_OP, NEW.change_id, NEW.date_created, NEW.date_modified, NEW.date_published, NEW.date_updated, NEW.description, NEW.extra_id, NEW.extra_version_id, NEW.free_to_read_date, NEW.free_to_read_type, NEW.is_deleted, NEW.language, NEW.rights, NEW.same_as_id, NEW.same_as_version_id, NEW.title, NEW.type) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_abstractcreativework_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_abstractcreativework_change ON share_abstractcreativework;\n\n        CREATE TRIGGER share_abstractcreativework_change\n        BEFORE INSERT OR UPDATE ON share_abstractcreativework\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_abstractcreativework_change();',
            reverse_sql='DROP TRIGGER share_abstractcreativework_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_workidentifier_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_workidentifierversion(persistent_id, action, change_id, creative_work_id, creative_work_version_id, date_created, date_modified, extra_id, extra_version_id, host, same_as_id, same_as_version_id, scheme, uri) VALUES (NEW.id, TG_OP, NEW.change_id, NEW.creative_work_id, NEW.creative_work_version_id, NEW.date_created, NEW.date_modified, NEW.extra_id, NEW.extra_version_id, NEW.host, NEW.same_as_id, NEW.same_as_version_id, NEW.scheme, NEW.uri) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_workidentifier_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_workidentifier_change ON share_workidentifier;\n\n        CREATE TRIGGER share_workidentifier_change\n        BEFORE INSERT OR UPDATE ON share_workidentifier\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_workidentifier_change();',
            reverse_sql='DROP TRIGGER share_workidentifier_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_agentidentifier_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_agentidentifierversion(persistent_id, action, agent_id, agent_version_id, change_id, date_created, date_modified, extra_id, extra_version_id, host, same_as_id, same_as_version_id, scheme, uri) VALUES (NEW.id, TG_OP, NEW.agent_id, NEW.agent_version_id, NEW.change_id, NEW.date_created, NEW.date_modified, NEW.extra_id, NEW.extra_version_id, NEW.host, NEW.same_as_id, NEW.same_as_version_id, NEW.scheme, NEW.uri) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_agentidentifier_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_agentidentifier_change ON share_agentidentifier;\n\n        CREATE TRIGGER share_agentidentifier_change\n        BEFORE INSERT OR UPDATE ON share_agentidentifier\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_agentidentifier_change();',
            reverse_sql='DROP TRIGGER share_agentidentifier_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_abstractagentworkrelation_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_abstractagentworkrelationversion(persistent_id, action, agent_id, agent_version_id, bibliographic, change_id, cited_as, creative_work_id, creative_work_version_id, date_created, date_modified, extra_id, extra_version_id, order_cited, same_as_id, same_as_version_id, type) VALUES (NEW.id, TG_OP, NEW.agent_id, NEW.agent_version_id, NEW.bibliographic, NEW.change_id, NEW.cited_as, NEW.creative_work_id, NEW.creative_work_version_id, NEW.date_created, NEW.date_modified, NEW.extra_id, NEW.extra_version_id, NEW.order_cited, NEW.same_as_id, NEW.same_as_version_id, NEW.type) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_abstractagentworkrelation_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_abstractagentworkrelation_change ON share_abstractagentworkrelation;\n\n        CREATE TRIGGER share_abstractagentworkrelation_change\n        BEFORE INSERT OR UPDATE ON share_abstractagentworkrelation\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_abstractagentworkrelation_change();',
            reverse_sql='DROP TRIGGER share_abstractagentworkrelation_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_throughcontribution_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_throughcontributionversion(persistent_id, action, change_id, date_created, date_modified, extra_id, extra_version_id, related_id, related_version_id, same_as_id, same_as_version_id, subject_id, subject_version_id) VALUES (NEW.id, TG_OP, NEW.change_id, NEW.date_created, NEW.date_modified, NEW.extra_id, NEW.extra_version_id, NEW.related_id, NEW.related_version_id, NEW.same_as_id, NEW.same_as_version_id, NEW.subject_id, NEW.subject_version_id) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_throughcontribution_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_throughcontribution_change ON share_throughcontribution;\n\n        CREATE TRIGGER share_throughcontribution_change\n        BEFORE INSERT OR UPDATE ON share_throughcontribution\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_throughcontribution_change();',
            reverse_sql='DROP TRIGGER share_throughcontribution_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_award_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_awardversion(persistent_id, action, change_id, date_created, date_modified, description, extra_id, extra_version_id, name, same_as_id, same_as_version_id, url) VALUES (NEW.id, TG_OP, NEW.change_id, NEW.date_created, NEW.date_modified, NEW.description, NEW.extra_id, NEW.extra_version_id, NEW.name, NEW.same_as_id, NEW.same_as_version_id, NEW.url) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_award_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_award_change ON share_award;\n\n        CREATE TRIGGER share_award_change\n        BEFORE INSERT OR UPDATE ON share_award\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_award_change();',
            reverse_sql='DROP TRIGGER share_award_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_throughcontributionawards_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_throughcontributionawardsversion(persistent_id, action, award_id, award_version_id, change_id, contribution_id, contribution_version_id, date_created, date_modified, extra_id, extra_version_id, same_as_id, same_as_version_id) VALUES (NEW.id, TG_OP, NEW.award_id, NEW.award_version_id, NEW.change_id, NEW.contribution_id, NEW.contribution_version_id, NEW.date_created, NEW.date_modified, NEW.extra_id, NEW.extra_version_id, NEW.same_as_id, NEW.same_as_version_id) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_throughcontributionawards_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_throughcontributionawards_change ON share_throughcontributionawards;\n\n        CREATE TRIGGER share_throughcontributionawards_change\n        BEFORE INSERT OR UPDATE ON share_throughcontributionawards\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_throughcontributionawards_change();',
            reverse_sql='DROP TRIGGER share_throughcontributionawards_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_abstractworkrelation_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_abstractworkrelationversion(persistent_id, action, change_id, date_created, date_modified, extra_id, extra_version_id, related_id, related_version_id, same_as_id, same_as_version_id, subject_id, subject_version_id, type) VALUES (NEW.id, TG_OP, NEW.change_id, NEW.date_created, NEW.date_modified, NEW.extra_id, NEW.extra_version_id, NEW.related_id, NEW.related_version_id, NEW.same_as_id, NEW.same_as_version_id, NEW.subject_id, NEW.subject_version_id, NEW.type) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_abstractworkrelation_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_abstractworkrelation_change ON share_abstractworkrelation;\n\n        CREATE TRIGGER share_abstractworkrelation_change\n        BEFORE INSERT OR UPDATE ON share_abstractworkrelation\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_abstractworkrelation_change();',
            reverse_sql='DROP TRIGGER share_abstractworkrelation_change',
        ),
        migrations.RunSQL(
            sql='CREATE OR REPLACE FUNCTION before_share_abstractagentrelation_change() RETURNS trigger AS $$\n        DECLARE\n            vid INTEGER;\n        BEGIN\n            INSERT INTO share_abstractagentrelationversion(persistent_id, action, change_id, date_created, date_modified, extra_id, extra_version_id, related_id, related_version_id, same_as_id, same_as_version_id, subject_id, subject_version_id, type) VALUES (NEW.id, TG_OP, NEW.change_id, NEW.date_created, NEW.date_modified, NEW.extra_id, NEW.extra_version_id, NEW.related_id, NEW.related_version_id, NEW.same_as_id, NEW.same_as_version_id, NEW.subject_id, NEW.subject_version_id, NEW.type) RETURNING (id) INTO vid;\n            NEW.version_id = vid;\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql;',
            reverse_sql='DROP FUNCTION before_share_abstractagentrelation_change();',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS share_abstractagentrelation_change ON share_abstractagentrelation;\n\n        CREATE TRIGGER share_abstractagentrelation_change\n        BEFORE INSERT OR UPDATE ON share_abstractagentrelation\n        FOR EACH ROW\n        EXECUTE PROCEDURE before_share_abstractagentrelation_change();',
            reverse_sql='DROP TRIGGER share_abstractagentrelation_change',
        ),
    ]
