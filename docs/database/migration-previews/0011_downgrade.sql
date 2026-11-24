-- Running downgrade 0011 -> 0010

DELETE FROM access_role_permission WHERE access_role_permission.access_permission_id IN (SELECT access_permission.id 
FROM access_permission 
WHERE access_permission.code IN ('training.records.view', 'competency.view', 'competency.manage', 'competency.assess', 'imports.organisation.run', 'imports.organisation.commit'));

DELETE FROM access_permission WHERE access_permission.code IN ('training.records.view', 'competency.view', 'competency.manage', 'competency.assess', 'imports.organisation.run', 'imports.organisation.commit');

DELETE FROM proficiency_level;

DELETE FROM proficiency_scale;

DROP TABLE training_session;

DROP TABLE training_participation;

DROP TABLE notification;

DROP TABLE training_event;

DROP TABLE skill_matrix_member;

DROP TABLE skill_matrix_item;

DROP TABLE competency_assessment;

DROP TABLE training_programme;

DROP TABLE skill_matrix;

DROP TABLE competency_level_descriptor;

DROP TABLE competency_band_requirement;

DROP TABLE competency;

DROP TABLE proficiency_level;

DROP TABLE proficiency_scale;

DROP TABLE notification_preference;

UPDATE alembic_version SET version_num='0010' WHERE alembic_version.version_num = '0011';

