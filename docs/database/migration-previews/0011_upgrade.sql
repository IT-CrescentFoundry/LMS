-- Running upgrade 0010 -> 0011

CREATE TABLE notification_preference (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    user_account_id BIGINT UNSIGNED NOT NULL, 
    notification_type VARCHAR(50) NOT NULL, 
    in_app_enabled BOOL NOT NULL, 
    updated_at DATETIME(6) NOT NULL, 
    CONSTRAINT pk_notification_preference PRIMARY KEY (id), 
    CONSTRAINT fk_notification_preference_user_account_id_user_account FOREIGN KEY(user_account_id) REFERENCES user_account (id), 
    CONSTRAINT uq_notification_preference_user_account_id_notification_type UNIQUE (user_account_id, notification_type)
);

CREATE TABLE proficiency_scale (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    code VARCHAR(50) NOT NULL, 
    name VARCHAR(150) NOT NULL, 
    description VARCHAR(1000), 
    gap_method VARCHAR(10) NOT NULL, 
    source_note VARCHAR(500), 
    competent_rank SMALLINT, 
    plan_gap_steps SMALLINT, 
    is_active BOOL NOT NULL, 
    public_id BINARY(16) NOT NULL, 
    created_at DATETIME(6) NOT NULL, 
    updated_at DATETIME(6) NOT NULL, 
    version INTEGER NOT NULL, 
    created_by_user_id BIGINT UNSIGNED, 
    updated_by_user_id BIGINT UNSIGNED, 
    CONSTRAINT pk_proficiency_scale PRIMARY KEY (id), 
    CONSTRAINT ck_proficiency_scale_gap_method CHECK (gap_method IN ('ordinal', 'numeric')), 
    CONSTRAINT fk_proficiency_scale_created_by_user_id_user_account FOREIGN KEY(created_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT fk_proficiency_scale_updated_by_user_id_user_account FOREIGN KEY(updated_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT uq_proficiency_scale_code UNIQUE (code), 
    CONSTRAINT uq_proficiency_scale_public_id UNIQUE (public_id)
);

CREATE TABLE proficiency_level (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    scale_id BIGINT UNSIGNED NOT NULL, 
    `rank` SMALLINT NOT NULL, 
    code VARCHAR(30) NOT NULL, 
    label VARCHAR(150) NOT NULL, 
    numeric_value NUMERIC(6, 2), 
    description VARCHAR(1000), 
    public_id BINARY(16) NOT NULL, 
    CONSTRAINT pk_proficiency_level PRIMARY KEY (id), 
    CONSTRAINT ck_proficiency_level_rank_non_negative CHECK (`rank` >= 0), 
    CONSTRAINT fk_proficiency_level_scale_id_proficiency_scale FOREIGN KEY(scale_id) REFERENCES proficiency_scale (id), 
    CONSTRAINT uq_proficiency_level_public_id UNIQUE (public_id), 
    CONSTRAINT uq_proficiency_level_scale_id_code UNIQUE (scale_id, code), 
    CONSTRAINT uq_proficiency_level_scale_id_rank UNIQUE (scale_id, `rank`)
);

CREATE TABLE competency (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    code VARCHAR(50) NOT NULL, 
    name VARCHAR(250) NOT NULL, 
    category VARCHAR(150), 
    sub_category VARCHAR(150), 
    description TEXT, 
    assessment_criteria TEXT, 
    applicability VARCHAR(1000), 
    scale_id BIGINT UNSIGNED, 
    owner_org_unit_id BIGINT UNSIGNED, 
    source_ref VARCHAR(200), 
    is_active BOOL NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    approved_at DATETIME(6), 
    approved_by_user_id BIGINT UNSIGNED, 
    public_id BINARY(16) NOT NULL, 
    created_at DATETIME(6) NOT NULL, 
    updated_at DATETIME(6) NOT NULL, 
    version INTEGER NOT NULL, 
    created_by_user_id BIGINT UNSIGNED, 
    updated_by_user_id BIGINT UNSIGNED, 
    CONSTRAINT pk_competency PRIMARY KEY (id), 
    CONSTRAINT ck_competency_status CHECK (status IN ('draft', 'approved')), 
    CONSTRAINT ck_competency_approved_has_time CHECK (status <> 'approved' OR approved_at IS NOT NULL), 
    CONSTRAINT fk_competency_approved_by_user_id_user_account FOREIGN KEY(approved_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT fk_competency_created_by_user_id_user_account FOREIGN KEY(created_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT fk_competency_owner_org_unit_id_org_unit FOREIGN KEY(owner_org_unit_id) REFERENCES org_unit (id), 
    CONSTRAINT fk_competency_scale_id_proficiency_scale FOREIGN KEY(scale_id) REFERENCES proficiency_scale (id), 
    CONSTRAINT fk_competency_updated_by_user_id_user_account FOREIGN KEY(updated_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT uq_competency_code UNIQUE (code), 
    CONSTRAINT uq_competency_public_id UNIQUE (public_id)
);

CREATE INDEX ix_competency_category ON competency (category);

CREATE INDEX ix_competency_name ON competency (name);

CREATE INDEX ix_competency_status ON competency (status);

CREATE TABLE competency_band_requirement (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    competency_id BIGINT UNSIGNED NOT NULL, 
    band_code VARCHAR(30) NOT NULL, 
    band_label VARCHAR(150), 
    required_level_id BIGINT UNSIGNED, 
    CONSTRAINT pk_competency_band_requirement PRIMARY KEY (id), 
    CONSTRAINT fk_competency_band_requirement_competency_id_competency FOREIGN KEY(competency_id) REFERENCES competency (id), 
    CONSTRAINT fk_competency_band_requirement_required_level_id_profici_5a14 FOREIGN KEY(required_level_id) REFERENCES proficiency_level (id), 
    CONSTRAINT uq_competency_band_requirement_competency_id_band_code UNIQUE (competency_id, band_code)
);

CREATE TABLE competency_level_descriptor (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    competency_id BIGINT UNSIGNED NOT NULL, 
    level_id BIGINT UNSIGNED NOT NULL, 
    description VARCHAR(2000) NOT NULL, 
    CONSTRAINT pk_competency_level_descriptor PRIMARY KEY (id), 
    CONSTRAINT fk_competency_level_descriptor_competency_id_competency FOREIGN KEY(competency_id) REFERENCES competency (id), 
    CONSTRAINT fk_competency_level_descriptor_level_id_proficiency_level FOREIGN KEY(level_id) REFERENCES proficiency_level (id), 
    CONSTRAINT uq_competency_level_descriptor_competency_id_level_id UNIQUE (competency_id, level_id)
);

CREATE TABLE skill_matrix (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    code VARCHAR(50) NOT NULL, 
    name VARCHAR(250) NOT NULL, 
    description VARCHAR(1000), 
    org_unit_id BIGINT UNSIGNED, 
    location_id BIGINT UNSIGNED, 
    designation_id BIGINT UNSIGNED, 
    functional_role_id BIGINT UNSIGNED, 
    scale_id BIGINT UNSIGNED NOT NULL, 
    risk_medium_margin SMALLINT NOT NULL, 
    is_active BOOL NOT NULL, 
    public_id BINARY(16) NOT NULL, 
    created_at DATETIME(6) NOT NULL, 
    updated_at DATETIME(6) NOT NULL, 
    version INTEGER NOT NULL, 
    created_by_user_id BIGINT UNSIGNED, 
    updated_by_user_id BIGINT UNSIGNED, 
    CONSTRAINT pk_skill_matrix PRIMARY KEY (id), 
    CONSTRAINT fk_skill_matrix_created_by_user_id_user_account FOREIGN KEY(created_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT fk_skill_matrix_designation_id_designation FOREIGN KEY(designation_id) REFERENCES designation (id), 
    CONSTRAINT fk_skill_matrix_functional_role_id_functional_role FOREIGN KEY(functional_role_id) REFERENCES functional_role (id), 
    CONSTRAINT fk_skill_matrix_location_id_location FOREIGN KEY(location_id) REFERENCES location (id), 
    CONSTRAINT fk_skill_matrix_org_unit_id_org_unit FOREIGN KEY(org_unit_id) REFERENCES org_unit (id), 
    CONSTRAINT fk_skill_matrix_scale_id_proficiency_scale FOREIGN KEY(scale_id) REFERENCES proficiency_scale (id), 
    CONSTRAINT fk_skill_matrix_updated_by_user_id_user_account FOREIGN KEY(updated_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT uq_skill_matrix_code UNIQUE (code), 
    CONSTRAINT uq_skill_matrix_public_id UNIQUE (public_id)
);

CREATE INDEX ix_skill_matrix_location_id ON skill_matrix (location_id);

CREATE INDEX ix_skill_matrix_org_unit_id ON skill_matrix (org_unit_id);

CREATE TABLE training_programme (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    code VARCHAR(50) NOT NULL, 
    title VARCHAR(250) NOT NULL, 
    category VARCHAR(100), 
    description TEXT, 
    objectives TEXT, 
    target_audience VARCHAR(500), 
    default_delivery_mode VARCHAR(20), 
    standard_duration_minutes INTEGER, 
    competency_id BIGINT UNSIGNED, 
    is_active BOOL NOT NULL, 
    public_id BINARY(16) NOT NULL, 
    created_at DATETIME(6) NOT NULL, 
    updated_at DATETIME(6) NOT NULL, 
    version INTEGER NOT NULL, 
    created_by_user_id BIGINT UNSIGNED, 
    updated_by_user_id BIGINT UNSIGNED, 
    CONSTRAINT pk_training_programme PRIMARY KEY (id), 
    CONSTRAINT ck_training_programme_mode CHECK (default_delivery_mode IS NULL OR default_delivery_mode IN ('classroom', 'online', 'hybrid', 'ojt')), 
    CONSTRAINT ck_training_programme_duration CHECK (standard_duration_minutes IS NULL OR standard_duration_minutes > 0), 
    CONSTRAINT fk_training_programme_competency_id_competency FOREIGN KEY(competency_id) REFERENCES competency (id), 
    CONSTRAINT fk_training_programme_created_by_user_id_user_account FOREIGN KEY(created_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT fk_training_programme_updated_by_user_id_user_account FOREIGN KEY(updated_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT uq_training_programme_code UNIQUE (code), 
    CONSTRAINT uq_training_programme_public_id UNIQUE (public_id)
);

CREATE INDEX ix_training_programme_category ON training_programme (category);

CREATE INDEX ix_training_programme_title ON training_programme (title);

CREATE TABLE competency_assessment (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    employee_id BIGINT UNSIGNED NOT NULL, 
    competency_id BIGINT UNSIGNED NOT NULL, 
    level_id BIGINT UNSIGNED NOT NULL, 
    assessed_on DATE NOT NULL, 
    method VARCHAR(30) NOT NULL, 
    assessor_employee_id BIGINT UNSIGNED, 
    assessor_name VARCHAR(200), 
    evidence VARCHAR(2000), 
    matrix_id BIGINT UNSIGNED, 
    recorded_at DATETIME(6) NOT NULL, 
    recorded_by_user_id BIGINT UNSIGNED, 
    public_id BINARY(16) NOT NULL, 
    CONSTRAINT pk_competency_assessment PRIMARY KEY (id), 
    CONSTRAINT ck_competency_assessment_method CHECK (method IN ('assessor_rating', 'manager_rating', 'practical_evaluation', 'imported_matrix')), 
    CONSTRAINT fk_competency_assessment_assessor_employee_id_employee FOREIGN KEY(assessor_employee_id) REFERENCES employee (id), 
    CONSTRAINT fk_competency_assessment_competency_id_competency FOREIGN KEY(competency_id) REFERENCES competency (id), 
    CONSTRAINT fk_competency_assessment_employee_id_employee FOREIGN KEY(employee_id) REFERENCES employee (id), 
    CONSTRAINT fk_competency_assessment_level_id_proficiency_level FOREIGN KEY(level_id) REFERENCES proficiency_level (id), 
    CONSTRAINT fk_competency_assessment_matrix_id_skill_matrix FOREIGN KEY(matrix_id) REFERENCES skill_matrix (id), 
    CONSTRAINT fk_competency_assessment_recorded_by_user_id_user_account FOREIGN KEY(recorded_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT uq_competency_assessment_public_id UNIQUE (public_id)
);

CREATE INDEX ix_competency_assessment_competency_id ON competency_assessment (competency_id);

CREATE INDEX ix_competency_assessment_current ON competency_assessment (employee_id, competency_id, assessed_on);

CREATE TABLE skill_matrix_item (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    matrix_id BIGINT UNSIGNED NOT NULL, 
    competency_id BIGINT UNSIGNED NOT NULL, 
    required_level_id BIGINT UNSIGNED, 
    required_headcount INTEGER, 
    group_label VARCHAR(150), 
    display_order INTEGER NOT NULL, 
    created_at DATETIME(6) NOT NULL, 
    CONSTRAINT pk_skill_matrix_item PRIMARY KEY (id), 
    CONSTRAINT fk_skill_matrix_item_competency_id_competency FOREIGN KEY(competency_id) REFERENCES competency (id), 
    CONSTRAINT fk_skill_matrix_item_matrix_id_skill_matrix FOREIGN KEY(matrix_id) REFERENCES skill_matrix (id), 
    CONSTRAINT fk_skill_matrix_item_required_level_id_proficiency_level FOREIGN KEY(required_level_id) REFERENCES proficiency_level (id), 
    CONSTRAINT uq_skill_matrix_item_matrix_id_competency_id UNIQUE (matrix_id, competency_id)
);

CREATE TABLE skill_matrix_member (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    matrix_id BIGINT UNSIGNED NOT NULL, 
    employee_id BIGINT UNSIGNED NOT NULL, 
    added_at DATETIME(6) NOT NULL, 
    added_by_user_id BIGINT UNSIGNED, 
    CONSTRAINT pk_skill_matrix_member PRIMARY KEY (id), 
    CONSTRAINT fk_skill_matrix_member_added_by_user_id_user_account FOREIGN KEY(added_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT fk_skill_matrix_member_employee_id_employee FOREIGN KEY(employee_id) REFERENCES employee (id), 
    CONSTRAINT fk_skill_matrix_member_matrix_id_skill_matrix FOREIGN KEY(matrix_id) REFERENCES skill_matrix (id), 
    CONSTRAINT uq_skill_matrix_member_matrix_id_employee_id UNIQUE (matrix_id, employee_id)
);

CREATE INDEX ix_skill_matrix_member_employee_id ON skill_matrix_member (employee_id);

CREATE TABLE training_event (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    code VARCHAR(50) NOT NULL, 
    programme_id BIGINT UNSIGNED, 
    title VARCHAR(250) NOT NULL, 
    description TEXT, 
    status VARCHAR(20) NOT NULL, 
    delivery_mode VARCHAR(20), 
    org_unit_id BIGINT UNSIGNED, 
    location_id BIGINT UNSIGNED, 
    calendar_label VARCHAR(150), 
    planned_month DATE, 
    planned_start_date DATE, 
    planned_end_date DATE, 
    actual_start_date DATE, 
    actual_end_date DATE, 
    planned_duration_minutes INTEGER, 
    venue VARCHAR(250), 
    online_join_url VARCHAR(500), 
    trainer_type VARCHAR(10), 
    trainer_employee_id BIGINT UNSIGNED, 
    trainer_name VARCHAR(200), 
    provider_name VARCHAR(200), 
    capacity INTEGER, 
    planned_participant_count INTEGER, 
    reported_attendance_count INTEGER, 
    target_audience VARCHAR(500), 
    instructions TEXT, 
    status_reason VARCHAR(500), 
    source VARCHAR(10) NOT NULL, 
    published_at DATETIME(6), 
    public_id BINARY(16) NOT NULL, 
    created_at DATETIME(6) NOT NULL, 
    updated_at DATETIME(6) NOT NULL, 
    version INTEGER NOT NULL, 
    created_by_user_id BIGINT UNSIGNED, 
    updated_by_user_id BIGINT UNSIGNED, 
    CONSTRAINT pk_training_event PRIMARY KEY (id), 
    CONSTRAINT ck_training_event_mode CHECK (delivery_mode IS NULL OR delivery_mode IN ('classroom', 'online', 'hybrid', 'ojt')), 
    CONSTRAINT ck_training_event_source CHECK (source IN ('manual', 'import')), 
    CONSTRAINT ck_training_event_completed_has_dates CHECK (status <> 'completed' OR actual_start_date IS NOT NULL), 
    CONSTRAINT ck_training_event_status CHECK (status IN ('planned', 'scheduled', 'completed', 'postponed', 'cancelled')), 
    CONSTRAINT ck_training_event_trainer_type CHECK (trainer_type IS NULL OR trainer_type IN ('internal', 'external')), 
    CONSTRAINT ck_training_event_actual_period CHECK (actual_end_date IS NULL OR actual_start_date IS NULL OR actual_end_date >= actual_start_date), 
    CONSTRAINT ck_training_event_capacity CHECK (capacity IS NULL OR capacity > 0), 
    CONSTRAINT ck_training_event_duration CHECK (planned_duration_minutes IS NULL OR planned_duration_minutes > 0), 
    CONSTRAINT ck_training_event_planned_period CHECK (planned_end_date IS NULL OR planned_start_date IS NULL OR planned_end_date >= planned_start_date), 
    CONSTRAINT ck_training_event_month_first_day CHECK (planned_month IS NULL OR DAY(planned_month) = 1), 
    CONSTRAINT ck_training_event_planned_count CHECK (planned_participant_count IS NULL OR planned_participant_count >= 0), 
    CONSTRAINT ck_training_event_reported_count CHECK (reported_attendance_count IS NULL OR reported_attendance_count >= 0), 
    CONSTRAINT fk_training_event_created_by_user_id_user_account FOREIGN KEY(created_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT fk_training_event_location_id_location FOREIGN KEY(location_id) REFERENCES location (id), 
    CONSTRAINT fk_training_event_org_unit_id_org_unit FOREIGN KEY(org_unit_id) REFERENCES org_unit (id), 
    CONSTRAINT fk_training_event_programme_id_training_programme FOREIGN KEY(programme_id) REFERENCES training_programme (id), 
    CONSTRAINT fk_training_event_trainer_employee_id_employee FOREIGN KEY(trainer_employee_id) REFERENCES employee (id), 
    CONSTRAINT fk_training_event_updated_by_user_id_user_account FOREIGN KEY(updated_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT uq_training_event_code UNIQUE (code), 
    CONSTRAINT uq_training_event_public_id UNIQUE (public_id)
);

CREATE INDEX ix_training_event_actual_start_date ON training_event (actual_start_date);

CREATE INDEX ix_training_event_calendar_label ON training_event (calendar_label);

CREATE INDEX ix_training_event_location_id ON training_event (location_id);

CREATE INDEX ix_training_event_org_unit_id ON training_event (org_unit_id);

CREATE INDEX ix_training_event_planned_month ON training_event (planned_month);

CREATE INDEX ix_training_event_planned_start_date ON training_event (planned_start_date);

CREATE INDEX ix_training_event_programme_id ON training_event (programme_id);

CREATE INDEX ix_training_event_status ON training_event (status);

CREATE INDEX ix_training_event_title ON training_event (title);

CREATE TABLE notification (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    recipient_user_id BIGINT UNSIGNED NOT NULL, 
    notification_type VARCHAR(50) NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    body VARCHAR(1000) NOT NULL, 
    link_path VARCHAR(300), 
    training_event_id BIGINT UNSIGNED, 
    employee_id BIGINT UNSIGNED, 
    dedupe_key VARCHAR(200) NOT NULL, 
    created_at DATETIME(6) NOT NULL, 
    read_at DATETIME(6), 
    public_id BINARY(16) NOT NULL, 
    CONSTRAINT pk_notification PRIMARY KEY (id), 
    CONSTRAINT fk_notification_employee_id_employee FOREIGN KEY(employee_id) REFERENCES employee (id), 
    CONSTRAINT fk_notification_recipient_user_id_user_account FOREIGN KEY(recipient_user_id) REFERENCES user_account (id), 
    CONSTRAINT fk_notification_training_event_id_training_event FOREIGN KEY(training_event_id) REFERENCES training_event (id), 
    CONSTRAINT uq_notification_dedupe_key UNIQUE (dedupe_key), 
    CONSTRAINT uq_notification_public_id UNIQUE (public_id)
);

CREATE INDEX ix_notification_recipient_created ON notification (recipient_user_id, created_at);

CREATE INDEX ix_notification_recipient_read ON notification (recipient_user_id, read_at);

CREATE INDEX ix_notification_training_event_id ON notification (training_event_id);

CREATE TABLE training_participation (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    event_id BIGINT UNSIGNED NOT NULL, 
    employee_id BIGINT UNSIGNED NOT NULL, 
    nomination_status VARCHAR(20) NOT NULL, 
    attendance_status VARCHAR(20), 
    attended_minutes INTEGER, 
    completion_status VARCHAR(20), 
    assessment_result VARCHAR(100), 
    certificate_number VARCHAR(100), 
    remarks VARCHAR(1000), 
    source VARCHAR(10) NOT NULL, 
    attendance_recorded_at DATETIME(6), 
    attendance_recorded_by_user_id BIGINT UNSIGNED, 
    completion_recorded_at DATETIME(6), 
    completion_recorded_by_user_id BIGINT UNSIGNED, 
    public_id BINARY(16) NOT NULL, 
    created_at DATETIME(6) NOT NULL, 
    updated_at DATETIME(6) NOT NULL, 
    version INTEGER NOT NULL, 
    created_by_user_id BIGINT UNSIGNED, 
    updated_by_user_id BIGINT UNSIGNED, 
    CONSTRAINT pk_training_participation PRIMARY KEY (id), 
    CONSTRAINT ck_training_participation_attend CHECK (attendance_status IS NULL OR attendance_status IN ('present', 'partial', 'absent', 'excused')), 
    CONSTRAINT ck_training_participation_certificate_completed CHECK (certificate_number IS NULL OR completion_status = 'completed'), 
    CONSTRAINT ck_training_participation_completed_attended CHECK (completion_status IS NULL OR completion_status <> 'completed' OR attendance_status IN ('present', 'partial')), 
    CONSTRAINT ck_training_participation_completion CHECK (completion_status IS NULL OR completion_status IN ('completed', 'not_completed')), 
    CONSTRAINT ck_training_participation_nomination CHECK (nomination_status IN ('nominated', 'confirmed', 'withdrawn')), 
    CONSTRAINT ck_training_participation_source CHECK (source IN ('manual', 'import')), 
    CONSTRAINT ck_training_participation_minutes_non_negative CHECK (attended_minutes IS NULL OR attended_minutes >= 0), 
    CONSTRAINT fk_training_participation_attendance_recorded_by_user_id_2f3c FOREIGN KEY(attendance_recorded_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT fk_training_participation_completion_recorded_by_user_id_5333 FOREIGN KEY(completion_recorded_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT fk_training_participation_created_by_user_id_user_account FOREIGN KEY(created_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT fk_training_participation_employee_id_employee FOREIGN KEY(employee_id) REFERENCES employee (id), 
    CONSTRAINT fk_training_participation_event_id_training_event FOREIGN KEY(event_id) REFERENCES training_event (id), 
    CONSTRAINT fk_training_participation_updated_by_user_id_user_account FOREIGN KEY(updated_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT uq_training_participation_event_id_employee_id UNIQUE (event_id, employee_id), 
    CONSTRAINT uq_training_participation_public_id UNIQUE (public_id)
);

CREATE INDEX ix_training_participation_employee_id ON training_participation (employee_id);

CREATE INDEX ix_training_participation_event_id ON training_participation (event_id);

CREATE TABLE training_session (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
    event_id BIGINT UNSIGNED NOT NULL, 
    starts_at DATETIME(6) NOT NULL, 
    ends_at DATETIME(6) NOT NULL, 
    venue VARCHAR(250), 
    online_join_url VARCHAR(500), 
    status VARCHAR(20) NOT NULL, 
    notes VARCHAR(500), 
    public_id BINARY(16) NOT NULL, 
    created_at DATETIME(6) NOT NULL, 
    updated_at DATETIME(6) NOT NULL, 
    version INTEGER NOT NULL, 
    created_by_user_id BIGINT UNSIGNED, 
    updated_by_user_id BIGINT UNSIGNED, 
    CONSTRAINT pk_training_session PRIMARY KEY (id), 
    CONSTRAINT ck_training_session_status CHECK (status IN ('scheduled', 'cancelled')), 
    CONSTRAINT ck_training_session_period CHECK (ends_at > starts_at), 
    CONSTRAINT fk_training_session_created_by_user_id_user_account FOREIGN KEY(created_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT fk_training_session_event_id_training_event FOREIGN KEY(event_id) REFERENCES training_event (id), 
    CONSTRAINT fk_training_session_updated_by_user_id_user_account FOREIGN KEY(updated_by_user_id) REFERENCES user_account (id), 
    CONSTRAINT uq_training_session_public_id UNIQUE (public_id)
);

CREATE INDEX ix_training_session_event_id ON training_session (event_id);

CREATE INDEX ix_training_session_starts_at ON training_session (starts_at);

INSERT INTO access_permission (code, description, is_privileged, created_at) VALUES ('training.records.view', 'View every employee''s training records and the full calendar', false, utc_timestamp(6));

INSERT INTO access_permission (code, description, is_privileged, created_at) VALUES ('competency.view', 'View every employee''s skill matrices and competency assessments', false, utc_timestamp(6));

INSERT INTO access_permission (code, description, is_privileged, created_at) VALUES ('competency.manage', 'Maintain proficiency scales, the competency library and skill matrices', false, utc_timestamp(6));

INSERT INTO access_permission (code, description, is_privileged, created_at) VALUES ('competency.assess', 'Record assessed proficiency levels for employees', false, utc_timestamp(6));

INSERT INTO access_permission (code, description, is_privileged, created_at) VALUES ('imports.organisation.run', 'Upload, map, validate and cancel organisation-unit imports', false, utc_timestamp(6));

INSERT INTO access_permission (code, description, is_privileged, created_at) VALUES ('imports.organisation.commit', 'Approve and commit a validated organisation-unit import', false, utc_timestamp(6));

INSERT INTO access_role_permission (access_role_id, access_permission_id, granted_at) SELECT access_role.id, access_permission.id AS id_1, utc_timestamp(6) AS utc_timestamp_1 
FROM access_role INNER JOIN access_permission ON true = 1 
WHERE access_role.code = 'hr_admin' AND access_permission.code IN ('training.records.view', 'competency.view', 'competency.manage', 'competency.assess', 'imports.organisation.run', 'imports.organisation.commit');

INSERT INTO access_role_permission (access_role_id, access_permission_id, granted_at) SELECT access_role.id, access_permission.id AS id_1, utc_timestamp(6) AS utc_timestamp_1 
FROM access_role INNER JOIN access_permission ON true = 1 
WHERE access_role.code = 'super_admin' AND access_permission.code IN ('training.records.view', 'competency.view', 'competency.manage', 'competency.assess', 'imports.organisation.run', 'imports.organisation.commit');

INSERT INTO proficiency_scale (public_id, code, name, gap_method, competent_rank, plan_gap_steps, source_note, is_active, created_at, updated_at, version) VALUES (unhex(replace(uuid(), '-', '')), 'CF_SKILL_MATRIX_1_5', 'Skill matrix scale (1-5)', 'ordinal', 3, NULL, 'Training Calendar workbooks, skill-matrix legend; ''skilled'' = score >= 3', true, utc_timestamp(6), utc_timestamp(6), 1);

INSERT INTO proficiency_level (public_id, scale_id, `rank`, code, label, numeric_value) SELECT unhex(replace(uuid(), '-', '')) AS unhex_1, id, 1 AS anon_1, 'L1' AS anon_2, 'Beginner' AS anon_3, 1 AS anon_4 
FROM proficiency_scale 
WHERE code = 'CF_SKILL_MATRIX_1_5';

INSERT INTO proficiency_level (public_id, scale_id, `rank`, code, label, numeric_value) SELECT unhex(replace(uuid(), '-', '')) AS unhex_1, id, 2 AS anon_1, 'L2' AS anon_2, 'Can Work Under Supervision' AS anon_3, 2 AS anon_4 
FROM proficiency_scale 
WHERE code = 'CF_SKILL_MATRIX_1_5';

INSERT INTO proficiency_level (public_id, scale_id, `rank`, code, label, numeric_value) SELECT unhex(replace(uuid(), '-', '')) AS unhex_1, id, 3 AS anon_1, 'L3' AS anon_2, 'Can Work Independently' AS anon_3, 3 AS anon_4 
FROM proficiency_scale 
WHERE code = 'CF_SKILL_MATRIX_1_5';

INSERT INTO proficiency_level (public_id, scale_id, `rank`, code, label, numeric_value) SELECT unhex(replace(uuid(), '-', '')) AS unhex_1, id, 4 AS anon_1, 'L4' AS anon_2, 'Expert' AS anon_3, 4 AS anon_4 
FROM proficiency_scale 
WHERE code = 'CF_SKILL_MATRIX_1_5';

INSERT INTO proficiency_level (public_id, scale_id, `rank`, code, label, numeric_value) SELECT unhex(replace(uuid(), '-', '')) AS unhex_1, id, 5 AS anon_1, 'L5' AS anon_2, 'Can Train Others' AS anon_3, 5 AS anon_4 
FROM proficiency_scale 
WHERE code = 'CF_SKILL_MATRIX_1_5';

INSERT INTO proficiency_scale (public_id, code, name, gap_method, competent_rank, plan_gap_steps, source_note, is_active, created_at, updated_at, version) VALUES (unhex(replace(uuid(), '-', '')), 'CF_TC_LIBRARY_1_4', 'Technical competency library scale (1-4)', 'numeric', NULL, 2, 'CF Technical Competency Library, Read Me; gap = required - current, plan if >= 2', true, utc_timestamp(6), utc_timestamp(6), 1);

INSERT INTO proficiency_level (public_id, scale_id, `rank`, code, label, numeric_value) SELECT unhex(replace(uuid(), '-', '')) AS unhex_1, id, 1 AS anon_1, 'L1' AS anon_2, 'Foundation' AS anon_3, 1 AS anon_4 
FROM proficiency_scale 
WHERE code = 'CF_TC_LIBRARY_1_4';

INSERT INTO proficiency_level (public_id, scale_id, `rank`, code, label, numeric_value) SELECT unhex(replace(uuid(), '-', '')) AS unhex_1, id, 2 AS anon_1, 'L2' AS anon_2, 'Practitioner' AS anon_3, 2 AS anon_4 
FROM proficiency_scale 
WHERE code = 'CF_TC_LIBRARY_1_4';

INSERT INTO proficiency_level (public_id, scale_id, `rank`, code, label, numeric_value) SELECT unhex(replace(uuid(), '-', '')) AS unhex_1, id, 3 AS anon_1, 'L3' AS anon_2, 'Advanced' AS anon_3, 3 AS anon_4 
FROM proficiency_scale 
WHERE code = 'CF_TC_LIBRARY_1_4';

INSERT INTO proficiency_level (public_id, scale_id, `rank`, code, label, numeric_value) SELECT unhex(replace(uuid(), '-', '')) AS unhex_1, id, 4 AS anon_1, 'L4' AS anon_2, 'Expert' AS anon_3, 4 AS anon_4 
FROM proficiency_scale 
WHERE code = 'CF_TC_LIBRARY_1_4';

UPDATE alembic_version SET version_num='0011' WHERE alembic_version.version_num = '0010';

