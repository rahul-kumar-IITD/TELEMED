"""Initial schema: nine tables, CHECK constraints, indexes, append-only triggers.

Revision ID: 0001
Revises: None
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA_STATEMENTS = [
    "CREATE TABLE users ( user_id INTEGER NOT NULL, email VARCHAR(254) NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, active INTEGER DEFAULT '1' NOT NULL, created_at VARCHAR(26) NOT NULL, updated_at VARCHAR(26) NOT NULL, PRIMARY KEY (user_id), CONSTRAINT ck_users_email_lower CHECK (email = lower(email)), CONSTRAINT ck_users_password_hash CHECK (password_hash LIKE '$argon2%'), CONSTRAINT ck_users_role CHECK (role IN ('PATIENT','DOCTOR','ADMIN')), CONSTRAINT ck_users_active CHECK (active IN (0,1)), UNIQUE (email) )",
    "CREATE INDEX ix_users_role_active ON users (role, active)",
    "CREATE TABLE doctor_profiles ( doctor_id INTEGER NOT NULL, full_name VARCHAR(200) NOT NULL, specialty VARCHAR(100) NOT NULL, languages TEXT NOT NULL, fee_minor INTEGER NOT NULL, created_at VARCHAR(26) NOT NULL, updated_at VARCHAR(26) NOT NULL, PRIMARY KEY (doctor_id), CONSTRAINT ck_doctor_specialty CHECK (length(specialty) >= 1), CONSTRAINT ck_doctor_languages CHECK (json_valid(languages) AND json_array_length(languages) BETWEEN 1 AND 10), CONSTRAINT ck_doctor_fee CHECK (fee_minor >= 0), FOREIGN KEY(doctor_id) REFERENCES users (user_id) )",
    "CREATE INDEX ix_doctor_specialty ON doctor_profiles (lower(specialty))",
    "CREATE TABLE patient_profiles ( patient_id INTEGER NOT NULL, created_at VARCHAR(26) NOT NULL, PRIMARY KEY (patient_id), FOREIGN KEY(patient_id) REFERENCES users (user_id) )",
    "CREATE TABLE availability_templates ( template_id INTEGER NOT NULL, doctor_id INTEGER NOT NULL, weekday INTEGER NOT NULL, start_time VARCHAR(5) NOT NULL, end_time VARCHAR(5) NOT NULL, slot_length_minutes INTEGER NOT NULL, created_at VARCHAR(26) NOT NULL, PRIMARY KEY (template_id), CONSTRAINT ck_tpl_weekday CHECK (weekday BETWEEN 0 AND 6), CONSTRAINT ck_tpl_window CHECK (end_time > start_time), CONSTRAINT ck_tpl_length CHECK (slot_length_minutes > 0), FOREIGN KEY(doctor_id) REFERENCES doctor_profiles (doctor_id) )",
    "CREATE INDEX ix_templates_doctor_weekday ON availability_templates (doctor_id, weekday)",
    "CREATE TABLE patient_profile_versions ( version_id INTEGER NOT NULL, patient_id INTEGER NOT NULL, version_number INTEGER NOT NULL, full_name VARCHAR(200) NOT NULL, age INTEGER NOT NULL, gender TEXT NOT NULL, phone VARCHAR(32) NOT NULL, changed_by_user_id INTEGER NOT NULL, created_at VARCHAR(26) NOT NULL, PRIMARY KEY (version_id), CONSTRAINT ck_ppv_version CHECK (version_number >= 1), CONSTRAINT ck_ppv_full_name CHECK (length(trim(full_name)) >= 1), CONSTRAINT ck_ppv_age CHECK (age > 0 AND age <= 130), CONSTRAINT ck_ppv_gender CHECK (gender IN ('FEMALE','MALE','OTHER','UNDISCLOSED')), CONSTRAINT ck_ppv_phone CHECK (length(trim(phone)) >= 1), FOREIGN KEY(patient_id) REFERENCES patient_profiles (patient_id), FOREIGN KEY(changed_by_user_id) REFERENCES users (user_id) )",
    "CREATE UNIQUE INDEX uq_ppv_patient_version ON patient_profile_versions (patient_id, version_number)",
    "CREATE TABLE slots ( slot_id INTEGER NOT NULL, doctor_id INTEGER NOT NULL, start_time VARCHAR(26) NOT NULL, end_time VARCHAR(26) NOT NULL, status TEXT DEFAULT 'AVAILABLE' NOT NULL, created_at VARCHAR(26) NOT NULL, updated_at VARCHAR(26) NOT NULL, PRIMARY KEY (slot_id), CONSTRAINT ck_slots_window CHECK (end_time > start_time), CONSTRAINT ck_slots_status CHECK (status IN ('AVAILABLE','BOOKED','BLOCKED')), FOREIGN KEY(doctor_id) REFERENCES doctor_profiles (doctor_id) )",
    "CREATE INDEX ix_slots_doctor_status_start ON slots (doctor_id, status, start_time)",
    "CREATE INDEX ix_slots_status_start ON slots (status, start_time)",
    "CREATE UNIQUE INDEX uq_slots_doctor_start ON slots (doctor_id, start_time)",
    "CREATE TABLE appointments ( appointment_id INTEGER NOT NULL, patient_id INTEGER NOT NULL, doctor_id INTEGER NOT NULL, slot_id INTEGER NOT NULL, status TEXT DEFAULT 'BOOKED' NOT NULL, fee_minor INTEGER NOT NULL, created_at VARCHAR(26) NOT NULL, updated_at VARCHAR(26) NOT NULL, PRIMARY KEY (appointment_id), CONSTRAINT ck_appt_status CHECK (status IN ('BOOKED','CHECKED_IN','IN_PROGRESS','COMPLETED','CANCELLED','NO_SHOW')), CONSTRAINT ck_appt_fee CHECK (fee_minor >= 0), FOREIGN KEY(patient_id) REFERENCES patient_profiles (patient_id), FOREIGN KEY(doctor_id) REFERENCES doctor_profiles (doctor_id), FOREIGN KEY(slot_id) REFERENCES slots (slot_id) )",
    "CREATE INDEX ix_appt_doctor_status ON appointments (doctor_id, status)",
    "CREATE INDEX ix_appt_patient_status ON appointments (patient_id, status)",
    "CREATE INDEX ix_appt_slot ON appointments (slot_id)",
    "CREATE UNIQUE INDEX uq_appt_slot_live ON appointments (slot_id) WHERE status <> 'CANCELLED'",
    "CREATE TABLE appointment_events ( event_id INTEGER NOT NULL, appointment_id INTEGER NOT NULL, event_type TEXT NOT NULL, from_status TEXT, to_status TEXT NOT NULL, actor_user_id INTEGER NOT NULL, actor_role TEXT NOT NULL, old_slot_id INTEGER, new_slot_id INTEGER, created_at VARCHAR(26) NOT NULL, PRIMARY KEY (event_id), CONSTRAINT ck_ae_event_type CHECK (event_type IN ('BOOKED','CHECKED_IN','IN_PROGRESS','COMPLETED','CANCELLED','NO_SHOW','RESCHEDULED')), CONSTRAINT ck_ae_from CHECK (from_status IS NULL OR from_status IN ('BOOKED','CHECKED_IN','IN_PROGRESS','COMPLETED','CANCELLED','NO_SHOW')), CONSTRAINT ck_ae_to CHECK (to_status IN ('BOOKED','CHECKED_IN','IN_PROGRESS','COMPLETED','CANCELLED','NO_SHOW')), CONSTRAINT ck_ae_actor_role CHECK (actor_role IN ('PATIENT','DOCTOR','ADMIN')), CONSTRAINT ck_ae_reschedule_slots CHECK ((event_type = 'RESCHEDULED') = (old_slot_id IS NOT NULL AND new_slot_id IS NOT NULL)), FOREIGN KEY(appointment_id) REFERENCES appointments (appointment_id), FOREIGN KEY(actor_user_id) REFERENCES users (user_id), FOREIGN KEY(old_slot_id) REFERENCES slots (slot_id), FOREIGN KEY(new_slot_id) REFERENCES slots (slot_id) )",
    "CREATE INDEX ix_events_appt ON appointment_events (appointment_id, event_id)",
    "CREATE TABLE consultation_notes ( note_id INTEGER NOT NULL, appointment_id INTEGER NOT NULL, author_id INTEGER NOT NULL, text TEXT NOT NULL, created_at VARCHAR(26) NOT NULL, PRIMARY KEY (note_id), CONSTRAINT ck_cn_text CHECK (length(trim(text)) >= 1 AND length(text) <= 5000), FOREIGN KEY(appointment_id) REFERENCES appointments (appointment_id), FOREIGN KEY(author_id) REFERENCES doctor_profiles (doctor_id) )",
    "CREATE INDEX ix_notes_appt ON consultation_notes (appointment_id, note_id)",
]

TRIGGER_STATEMENTS = [
    "CREATE TRIGGER trg_ppv_no_update BEFORE UPDATE ON patient_profile_versions BEGIN SELECT RAISE(ABORT, 'patient_profile_versions is append-only'); END",
    "CREATE TRIGGER trg_ppv_no_delete BEFORE DELETE ON patient_profile_versions BEGIN SELECT RAISE(ABORT, 'patient_profile_versions is append-only'); END",
    "CREATE TRIGGER trg_ae_no_update BEFORE UPDATE ON appointment_events BEGIN SELECT RAISE(ABORT, 'appointment_events is append-only'); END",
    "CREATE TRIGGER trg_ae_no_delete BEFORE DELETE ON appointment_events BEGIN SELECT RAISE(ABORT, 'appointment_events is append-only'); END",
    "CREATE TRIGGER trg_cn_no_update BEFORE UPDATE ON consultation_notes BEGIN SELECT RAISE(ABORT, 'consultation_notes is append-only'); END",
    "CREATE TRIGGER trg_cn_no_delete BEFORE DELETE ON consultation_notes BEGIN SELECT RAISE(ABORT, 'consultation_notes is append-only'); END",
]


def upgrade() -> None:
    for statement in SCHEMA_STATEMENTS + TRIGGER_STATEMENTS:
        op.execute(statement)
