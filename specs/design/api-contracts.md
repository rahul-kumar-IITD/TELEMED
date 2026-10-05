# TeleMed API Contracts

Version: 1.0 (design). Base URL (dev): `http://localhost:8000`. The Vite dev server proxies `/api` and `/health` to it, so the browser uses same-origin relative paths.
Machine-readable twin: `api-contracts.schema.json` (OpenAPI 3.0.3). If the two ever disagree, this file is the narrative source and the JSON must be fixed.

## 0. Conventions

### 0.1 Naming, formats
- All JSON field names, query parameters and enum-valued fields are `snake_case` (enum VALUES are `UPPER_SNAKE`). IDs are positive integers (`user_id`, `doctor_id`, `patient_id`, `slot_id`, `appointment_id`, `note_id`). Note: `doctor_id` and `patient_id` are always equal to the owning `user_id` (1:1 profile tables keyed on user id).
- Datetimes: ISO 8601 / RFC 3339 **with a UTC offset**. Responses always emit UTC with a trailing `Z` (`2026-10-12T03:30:00Z`). Requests containing a naive datetime (no offset) get 422. The browser converts to local zone for patients; doctor/admin screens use `provider_timezone` from `GET /api/config`.
- Wall-clock template times are `HH:MM` 24h strings interpreted in the provider timezone (`PROVIDER_TIMEZONE`, default `UTC`).
- Dates: `YYYY-MM-DD`.
- Money: JSON **string** with exactly 2 decimals, regex `^\d+\.\d{2}$` (example `"500.00"`). Request fees are accepted as strings only; a JSON number, non-numeric, negative or >2-decimal value gets 422. No floats anywhere.
- Lists are returned as an envelope `{"items": [...], "total": <int>}`. There is no pagination (prototype scale).
- Unknown request body fields are ignored (this is how a client-supplied `role` on registration is dropped), never trusted.
- No API version prefix. Routes are under `/api/...`.

### 0.2 Authentication
- Scheme: `Authorization: Bearer <access_token>` (JWT HS256). Claims: `sub` (user_id as string), `iat`, `exp`, `jti`, `role` (informational only, never trusted).
- On every protected request the server loads the user row, rejects inactive users (401), and takes the role **from the database**.
- Auth column legend used below: `Public`, `Any authenticated`, or a role list (`PATIENT`, `DOCTOR`, `ADMIN`). `ADMIN` may call every **id-addressed read** (`GET` with an id in the path: patient profiles, appointments, notes, doctors/slots) regardless of the role list, edit patient profiles (AC-01), list/deactivate/reactivate users and onboard doctors. `ADMIN` may NOT book, cancel, reschedule, change the status of, or add notes to appointments on behalf of others (403), and gets 403 on role-specific `/me` routes (admin has no personal profile, appointment list or queue). Patient profiles are editable only by the owning patient (`PUT /api/patients/me/profile`) or an admin (`PUT /api/admin/patients/{patient_id}/profile`); a doctor or another patient is refused (403, or 404 for a foreign id on a patient-addressed route).

### 0.2.1 Permission matrix
`R` = allowed, `403` = authenticated but refused, `own` = only the caller's own object (a foreign object is 404), `-` = not applicable. Anonymous callers get 401 on every non-public route.

| Capability (API) | PATIENT | DOCTOR | ADMIN |
|---|---|---|---|
| Register / login (API-03/04) | public | public | public |
| `GET /api/auth/me` (API-05) | R | R | R |
| Own profile `GET/PUT /api/patients/me/profile` (API-06/07) | R | 403 | 403 |
| `GET /api/patients/{patient_id}/profile` (API-08) | own | 403 | R (any) |
| Edit a patient's profile `PUT /api/admin/patients/{patient_id}/profile` (API-20) | 403 | 403 | R |
| Doctors list / detail / slots (API-09/10/11) | R | R | R |
| Own slots, block/unblock, queue (API-12/13/14/15) | 403 | R | 403 |
| Onboard doctor (API-16) | 403 | 403 | R |
| List users, deactivate, reactivate (API-17/18/19) | 403 | 403 | R |
| Book appointment (API-21) | R | 403 | 403 |
| `GET /api/appointments/mine` (API-22) | R | 403 | 403 |
| `GET /api/appointments/{id}` (API-23) | own | own | R (any, read-only) |
| Cancel (API-24) | own | own | 403 |
| Reschedule (API-25) | own | 403 | 403 |
| Change status (API-26) | 403 | own | 403 |
| Add note (API-27) | 403 | own | 403 |
| Read notes (API-28/29) | own | own | R (any) |
- Access rule order: 401 (no/bad/expired token or inactive user) -> 403 (role not allowed on the route) -> 404 (right role, but another user's object or object does not exist) -> 422 (malformed input) -> 409 (valid request refused by state or business rule).
  Note: validation of path/body input runs after the 401/403 checks, and ownership 404 runs before state 409.

### 0.3 Common headers
| Header | Direction | Rule |
|---|---|---|
| `X-Request-ID` | request (optional) / response (always) | Echoed if it matches `^[A-Za-z0-9._-]{1,64}$`, otherwise a generated UUIDv4 replaces it. Same value is the `correlation_id` in logs. |
| `Authorization` | request | `Bearer <jwt>` on all non-public routes. |
| `Content-Type` | request/response | `application/json` for bodies. |
| `Allow` | response on 405 | Lists permitted methods. |

### 0.4 Error body (all non-2xx responses)
```json
{ "code": "SLOT_UNAVAILABLE", "message": "That slot is no longer available.", "errors": [ { "field": "slot_id", "message": "..." } ] }
```
- `code` (string, enum below) and `message` (string, human readable, generic, never contains SQL, stack traces, PHI or echoed user input) are always present. `errors` is present only on 422 (field-level detail). The body deliberately contains no per-request data (no correlation id; use the `X-Request-ID` response header) so that repeated identical failures, notably login 401, are byte-identical.
- `errors[].field` is a dotted/indexed path into the request, e.g. `availability_templates[0].end_time`, `fee`, `password`.

| HTTP | `code` | Meaning |
|---|---|---|
| 401 | `UNAUTHENTICATED` | Missing, malformed, expired token, or user inactive. |
| 401 | `INVALID_CREDENTIALS` | Login failed (wrong password, unknown email, deactivated). Message always `"Invalid email or password."` |
| 403 | `FORBIDDEN` | Authenticated, wrong role for the route. |
| 404 | `NOT_FOUND` | Object missing OR belongs to someone else (indistinguishable by design). |
| 405 | `METHOD_NOT_ALLOWED` | e.g. PUT/PATCH/DELETE on a note. |
| 409 | `EMAIL_ALREADY_REGISTERED` | Duplicate email (register, onboard). |
| 409 | `SLOT_UNAVAILABLE` | `SlotUnavailableException`: slot booked/blocked/past/outside window/other doctor's/doctor inactive/same slot. |
| 409 | `INVALID_APPOINTMENT_STATE` | `InvalidAppointmentStateException`: transition not allowed by the state machine, NO_SHOW before start, note on non-COMPLETED. |
| 409 | `CHANGE_WINDOW_CLOSED` | Patient cancel/reschedule less than 60 minutes before start (or after start). |
| 409 | `INVALID_SLOT_STATE` | Block of non-AVAILABLE slot; unblock of non-BLOCKED slot. |
| 409 | `ACTIVE_APPOINTMENTS_EXIST` | Deactivating a doctor with BOOKED/CHECKED_IN/IN_PROGRESS appointments. |
| 409 | `CANNOT_DEACTIVATE_SELF` | Admin deactivating own account. |
| 422 | `VALIDATION_ERROR` | Malformed input: bad types, naive datetime, bad fee, bad template, password length, note length, enum. |
| 503 | `SERVICE_UNAVAILABLE` | SQLite lock timeout. Message `"The service is busy, please try again."`. |
| 500 | `INTERNAL_ERROR` | Anything unhandled. Generic message. |

### 0.5 Rate limits
Rate limiting is **out of scope** (BRD section 5). Every endpoint below is `Rate limit: none`. The only throttle is SQLite write serialisation. Production recommendation (not implemented): 10 login attempts/minute/IP and 120 requests/minute/user at the reverse proxy.

### 0.6 Shared schemas (referenced by name below)

**User** `{ user_id:int, email:string, role:"PATIENT"|"DOCTOR"|"ADMIN", active:bool, full_name:string|null, created_at:datetime }`

**PatientProfile** `{ patient_id:int, version_number:int>=1, full_name:string (1..200), age:int (0 < age <= 130), gender:"FEMALE"|"MALE"|"OTHER"|"UNDISCLOSED", phone:string (1..32), updated_at:datetime }`. All four profile fields are required and never null (AC-01: name, age, gender, contact details).

**AvailabilityTemplate** (request/response) `{ weekday:int 0-6 (0=Monday), start_time:"HH:MM", end_time:"HH:MM", slot_length_minutes:int }`; response additionally has `template_id:int`.

**DoctorSummary** `{ doctor_id:int, full_name:string, specialty:string, languages:string[], fee:string, earliest_slot:datetime|null }`

**Slot** `{ slot_id:int, doctor_id:int, start_time:datetime, end_time:datetime, status:"AVAILABLE"|"BOOKED"|"BLOCKED" }`

**Appointment**
```json
{
  "appointment_id": 42,
  "status": "BOOKED",
  "slot_id": 311,
  "start_time": "2026-10-12T03:30:00Z",
  "end_time": "2026-10-12T04:00:00Z",
  "doctor":  { "doctor_id": 7, "full_name": "Dr. Asha Rao", "specialty": "Cardiology" },
  "patient": { "patient_id": 12, "full_name": "Test Patient" },
  "fee": "500.00",
  "allowed_actions": ["CANCEL", "RESCHEDULE"],
  "join_url": "https://video.example.test/visit/42",
  "change_deadline": "2026-10-12T02:30:00Z",
  "created_at": "2026-10-05T10:00:00Z",
  "updated_at": "2026-10-05T10:00:00Z"
}
```
- `status` enum: `BOOKED | CHECKED_IN | IN_PROGRESS | COMPLETED | CANCELLED | NO_SHOW`.
- `fee` is the fee snapshot taken at booking time.
- `change_deadline` = `start_time - 60 min`; the last instant a patient may cancel/reschedule (inclusive). UI uses it only for the explanatory text.
- `allowed_actions` (computed server-side for the **caller's role and the current clock**; the frontend renders exactly these and never re-implements the state machine). Vocabulary: `CHECKED_IN`, `IN_PROGRESS`, `COMPLETED`, `NO_SHOW`, `CANCEL`, `RESCHEDULE`.
  - PATIENT, status BOOKED, `start_time - now >= 60 min`: `["CANCEL","RESCHEDULE"]`; inside the window or after start: `[]`. All other statuses: `[]`.
  - DOCTOR: BOOKED -> `CHECKED_IN`, `CANCEL`, plus `NO_SHOW` only once `now >= start_time`; CHECKED_IN -> `IN_PROGRESS`, plus `NO_SHOW` once `now >= start_time`; IN_PROGRESS -> `COMPLETED`; terminal -> `[]`.
  - ADMIN: always `[]` (read-only).
- `join_url`: non-null only for the patient and the doctor of the appointment while status in BOOKED/CHECKED_IN/IN_PROGRESS; otherwise `null` (admin always `null`). Produced by the `VideoService` stub.
- `patient` and `doctor.full_name` may be `null`/derived if the profile name is unset (doctor falls back to the email local part).

**ConsultationNote** `{ note_id:int, appointment_id:int, author_id:int, text:string(1..5000), created_at:datetime }`

---

## 1. System

### API-01 GET /health
- Story: E1-S2. Auth: Public. Rate limit: none.
- Request: no headers/params/body.
- 200: `{ "status": "ok" }` (within 1 s of the process listening; does no DB work beyond an optional trivial `SELECT 1`).
- Errors: none expected.

### API-02 GET /api/config
- Story: E5-S1 (supporting). Auth: Public. Rate limit: none.
- Request: none.
- 200: `{ "provider_timezone": "Asia/Kolkata", "slot_window_days": 14, "change_window_minutes": 60 }`
- Purpose: lets the UI label doctor/admin times and word the 60-minute explanation without hard-coding.

---

## 2. Auth

### API-03 POST /api/auth/register
- Story: E1-S3 (AC-01). Auth: Public. Rate limit: none.
- Headers: `Content-Type: application/json`; optional `X-Request-ID`.
- Body:
  | field | type | req | rule |
  |---|---|---|---|
  | `email` | string | yes | valid email, <=254 chars, stored lower-cased; uniqueness case-insensitive |
  | `password` | string | yes | 8..128 characters inclusive |
  | `full_name` | string | yes | 1..200 characters (whitespace-only rejected) |
  | `age` | integer | yes | JSON integer, `0 < age <= 130` (strings, floats, 0, negatives, >130 rejected) |
  | `gender` | string enum | yes | `FEMALE` \| `MALE` \| `OTHER` \| `UNDISCLOSED` |
  | `phone` | string | yes | contact number, 1..32 characters (`email` remains the login identity) |
  Any other field (including `role`) is ignored; created role is always `PATIENT`.
- 201: `{ "user_id": 12, "role": "PATIENT", "email": "p1@example.test" }` (never the password/hash). Also inserts the initial profile as `patient_profile_versions` version 1 (full_name, age, gender, phone) in the same transaction as the user row.
- Errors: 409 `EMAIL_ALREADY_REGISTERED`; 422 `VALIDATION_ERROR` with field-level `errors[]` for every missing or invalid field (e.g. `{ "field": "age", "message": "..." }`, `gender`, `phone`, `full_name`, `password`, `email`); no user row is created on 422.

### API-04 POST /api/auth/login
- Story: E1-S3. Auth: Public. Rate limit: none.
- Body: `{ "email": string, "password": string }` (both required, non-empty).
- 200:
  ```json
  { "access_token": "<jwt>", "token_type": "bearer", "expires_in": 1800, "expires_at": "2026-10-05T10:30:00Z",
    "user_id": 12, "role": "PATIENT" }
  ```
  Lifetime = `JWT_LIFETIME_MINUTES` (default 30). No refresh token.
- Errors: 401 `INVALID_CREDENTIALS` with the byte-identical body for wrong password, unknown email, and deactivated account (equalised hashing work to avoid timing leaks); 422 for missing fields.
- The frontend must NOT treat this 401 as "session expired"; it shows the single generic message.

### API-05 GET /api/auth/me
- Story: E1-S4 / E5-S1 (supporting). Auth: Any authenticated. Rate limit: none.
- 200: `User`.
- Errors: 401.

---

## 3. Patient profile

### API-06 GET /api/patients/me/profile
- Story: E1-S5. Auth: PATIENT. Rate limit: none.
- 200: `PatientProfile` (latest version).
- Errors: 401; 403 (doctor/admin).

### API-07 PUT /api/patients/me/profile
- Story: E1-S5. Auth: PATIENT. Rate limit: none.
- Body (partial PUT; all keys optional but at least one must be present): `{ "full_name": string, "age": int, "gender": enum, "phone": string }` with the same rules as registration. **Omitted fields carry forward from the current version.** Required fields cannot be cleared: an explicit `null` or empty value is 422.
- Behaviour: always INSERTs a new `patient_profile_versions` row (`version_number = latest + 1`); earlier rows are never touched. Logs only `user_id` and `version_number`.
- 200: `PatientProfile` (the new version).
- Errors: 401; 403 (doctor/admin; admins edit through API-20); 422 `VALIDATION_ERROR` with field-level `errors[]` (empty body, `age` outside 1..130 or not an integer, bad `gender`, blank/too-long `full_name`/`phone`, null).

### API-08 GET /api/patients/{patient_id}/profile
- Story: E1-S5, E1-S4, E4-S2. Auth: PATIENT (own id only), ADMIN (any, read-only oversight), DOCTOR is 403.
- Path: `patient_id` int.
- 200: `PatientProfile`.
- Errors: 401; 403 (doctor); 404 (patient asking for another patient's id, or id not a patient).

---

## 4. Doctors, search, slots

Route ordering: the literal `/api/doctors/me/...` routes MUST be registered before `/api/doctors/{doctor_id}...`.

### API-09 GET /api/doctors
- Story: E2-S4. Auth: Any authenticated (patient UI primary; doctor/admin allowed). Rate limit: none.
- Query:
  | param | type | default | rule |
  |---|---|---|---|
  | `specialty` | string | - | case-insensitive exact match |
  | `language` | string | - | language code e.g. `hi`, matched against the doctor's `languages` (case-insensitive) |
  | `available_from` | datetime (tz-aware) | - | with `available_to`, keep only doctors with >=1 AVAILABLE slot with `start_time` in `[from, to]` |
  | `available_to` | datetime (tz-aware) | - | must be >= `available_from` else 422 |
  | `sort` | enum `earliest_slot`\|`fee`\|`name` | `earliest_slot` | ascending; doctors with no open slot sort last under `earliest_slot`; ties by `name` then `doctor_id` |
- Always excludes deactivated doctors. `earliest_slot` is the earliest AVAILABLE slot start with `now < start < now + 14d`.
- 200: `{ "items": [DoctorSummary], "total": 3 }`
- Errors: 401; 422 (naive datetime, bad `sort`, `available_to < available_from`).

### API-10 GET /api/doctors/{doctor_id}
- Story: E2-S4 (supporting, used by doctor detail page). Auth: Any authenticated.
- 200: `DoctorSummary`.
- Errors: 401; 404 (unknown or deactivated doctor).

### API-11 GET /api/doctors/{doctor_id}/slots
- Story: E2-S4. Auth: Any authenticated.
- Lists only `AVAILABLE` slots with `now < start_time < now + 14 days`, ordered by `start_time`. BOOKED, BLOCKED and past slots are never returned.
- 200: `{ "items": [Slot], "total": 6 }` (`status` is always `AVAILABLE`).
- Errors: 401; 404 (unknown or deactivated doctor).

### API-12 GET /api/doctors/me/slots
- Story: E2-S3. Auth: DOCTOR. Rate limit: none.
- Query: `from` (datetime tz-aware, default now), `to` (datetime tz-aware, default `from + 14 days`; `to >= from`, range capped at 31 days else 422). Note `from` is a Python keyword; the implementation aliases it.
- 200: `{ "items": [Slot], "total": n }` containing only the caller's slots, all statuses, ordered by `start_time`.
- Errors: 401; 403; 422.

### API-13 PUT /api/doctors/me/slots/{slot_id}/block
- Story: E2-S3. Auth: DOCTOR. No body.
- Single conditional UPDATE `AVAILABLE -> BLOCKED` where `doctor_id = caller`.
- 200: `Slot` (status `BLOCKED`).
- Errors: 401; 403; 404 (slot absent or another doctor's); 409 `INVALID_SLOT_STATE` (slot BOOKED or already BLOCKED; nothing changes).

### API-14 PUT /api/doctors/me/slots/{slot_id}/unblock
- Story: E2-S3. Auth: DOCTOR. No body.
- Conditional UPDATE `BLOCKED -> AVAILABLE`.
- 200: `Slot` (status `AVAILABLE`).
- Errors: 401; 403; 404; 409 `INVALID_SLOT_STATE` (slot not BLOCKED).

### API-15 GET /api/doctors/me/queue
- Story: E3-S5 (AC-08). Auth: DOCTOR.
- Query: `date` (`YYYY-MM-DD`, default today in provider zone). Day window = `[00:00, 24:00)` of that date in `PROVIDER_TIMEZONE`, converted to UTC.
- 200:
  ```json
  { "date": "2026-10-12", "timezone": "Asia/Kolkata", "items": [Appointment], "total": 1 }
  ```
  Only the caller's appointments (all statuses, incl. CANCELLED/NO_SHOW) whose slot `start_time` falls in the day; ordered ascending by `start_time`. Each `Appointment` carries `allowed_actions` for DOCTOR.
- Errors: 401; 403; 422 (bad date).

---

## 5. Admin

All admin endpoints: Auth `ADMIN` only (patient/doctor 403, anonymous 401). Rate limit: none.

### API-16 POST /api/admin/doctors
- Story: E2-S2 (AC-10).
- Body:
  | field | type | req | rule |
  |---|---|---|---|
  | `email` | string | yes | valid, unique case-insensitive |
  | `initial_password` | string | yes | 8..128 chars |
  | `full_name` | string | no | <=200; default = email local part |
  | `specialty` | string | yes | 1..100 |
  | `languages` | string[] | yes | 1..10 codes, each 2..8 chars `[a-z-]`, lower-cased, de-duplicated |
  | `fee` | string | yes | `^\d+\.\d{1,2}$`-style decimal, >=0, max 2 decimals (returned normalised `"500.00"`) |
  | `availability_templates` | AvailabilityTemplate[] | yes | 1..14 rows; each: `end_time > start_time`, `slot_length_minutes > 0` and divides the window exactly; rows for the same weekday must not overlap |
- Atomic: user (role DOCTOR), doctor_profile, templates and the first 14-day slot generation commit together, or nothing persists.
- 201:
  ```json
  { "doctor_id": 7, "user_id": 7, "email": "dr.rao@example.test", "full_name": "Dr. Asha Rao", "specialty": "Cardiology",
    "languages": ["en","hi"], "fee": "500.00",
    "availability_templates": [ { "template_id": 1, "weekday": 0, "start_time": "09:00", "end_time": "12:00", "slot_length_minutes": 30 } ],
    "slots_created": 12 }
  ```
- Errors: 401; 403; 409 `EMAIL_ALREADY_REGISTERED`; 422 `VALIDATION_ERROR` with `errors[].field` such as `fee`, `availability_templates[0].end_time`, `availability_templates[0].slot_length_minutes`.

### API-17 GET /api/admin/users
- Story: E4-S2.
- Query: `role` (`PATIENT`\|`DOCTOR`\|`ADMIN`, optional; bad value 422), `active` (bool, optional).
- 200: `{ "items": [User], "total": n }` ordered by `user_id`.
- Errors: 401; 403; 422.

### API-18 PUT /api/admin/users/{user_id}/deactivate
- Story: E4-S2. No body.
- Sets `active=false`. Patient: appointments untouched, doctor can still process them. Doctor: refused while any appointment is BOOKED/CHECKED_IN/IN_PROGRESS; doctor then disappears from search and slots cannot be booked. Idempotent on an already inactive user (200).
- 200: `User`.
- Errors: 401; 403; 404 (unknown user); 409 `CANNOT_DEACTIVATE_SELF`; 409 `ACTIVE_APPOINTMENTS_EXIST`.

### API-19 PUT /api/admin/users/{user_id}/reactivate
- Story: E4-S2. No body. Sets `active=true`. Idempotent.
- 200: `User`.
- Errors: 401; 403; 404.

### API-20 PUT /api/admin/patients/{patient_id}/profile
- Story: E4-S2 (AC-01). Auth: ADMIN only (patient/doctor 403). Body and semantics identical to API-07 (partial carry-forward, same field rules). Inserts a new version with `changed_by_user_id` = the admin.
- 200: `PatientProfile`.
- Errors: 401; 403; 404 (id missing or not a PATIENT); 422.

---

## 6. Appointments

### API-21 POST /api/appointments
- Story: E3-S2. Auth: PATIENT only (doctor/admin 403; admin never books on behalf of a patient). Rate limit: none.
- Body: `{ "slot_id": int }` (required).
- One transaction (`BEGIN IMMEDIATE`): conditional `UPDATE slots SET status='BOOKED' WHERE slot_id=? AND status='AVAILABLE' AND now < start_time < now+14d AND doctor active` -> must affect exactly 1 row, insert appointment (fee snapshot), insert `BOOKED` event. Then `PaymentService.charge` stub called once.
- 201: `Appointment` (`status: "BOOKED"`, `fee` string, `allowed_actions` for the patient, `join_url` set).
- Errors: 401; 403; 409 `SLOT_UNAVAILABLE` (slot BOOKED/BLOCKED/past/beyond 14 days/doctor inactive); 404 (slot id does not exist); 422 (missing/non-int). Under 20-way contention: exactly one 201, nineteen 409, zero 503.

### API-22 GET /api/appointments/mine
- Story: E4-S3. Auth: PATIENT. 
- Query: `status` (optional enum filter).
- 200: `{ "items": [Appointment], "total": n }` caller's only, ascending `start_time`.
- Errors: 401; 403.

### API-23 GET /api/appointments/{appointment_id}
- Story: E4-S3. Auth: PATIENT (own), DOCTOR (own as doctor), ADMIN (any appointment, read-only: `allowed_actions` is `[]`, `join_url` is `null`).
- 200: `Appointment` (allowed_actions/join_url computed for caller role).
- Errors: 401; 404 (missing or someone else's; including a doctor who is not this appointment's doctor).

### API-24 POST /api/appointments/{appointment_id}/cancel
- Story: E3-S3 (AC-06). Auth: PATIENT (own) or DOCTOR (own). Admin 403. No body.
- PATIENT: allowed iff status BOOKED and `start_time - now >= 60:00` (exactly 60:00 OK, 59:59 or after start refused). Appointment -> CANCELLED, slot -> AVAILABLE.
- DOCTOR: allowed iff status BOOKED, any time. Appointment -> CANCELLED, slot -> BLOCKED (so it is not rebooked).
- Both: one `CANCELLED` event with `actor_role`; `PaymentService.refund` stub called exactly once; nothing changes on refusal.
- 200: `Appointment`.
- Errors: 401; 403; 404 (not owner); 409 `CHANGE_WINDOW_CLOSED` (patient inside 60 min / after start); 409 `INVALID_APPOINTMENT_STATE` (status not BOOKED).

### API-25 POST /api/appointments/{appointment_id}/reschedule
- Story: E3-S4 (AC-07). Auth: PATIENT (own). Doctor/admin 403.
- Body: `{ "new_slot_id": int }`.
- Atomic: claim target slot (conditional UPDATE), release old slot to AVAILABLE, repoint `appointments.slot_id`, append one `RESCHEDULED` event with `old_slot_id`/`new_slot_id`. Any failure rolls the whole thing back. `appointment_id` unchanged.
- Target must be AVAILABLE, in `(now, now+14d)`, same doctor (active), and different from the current slot. Current appointment must be BOOKED and `start_time - now >= 60 min`.
- 200: `Appointment` (new slot times).
- Errors: 401; 403; 404 (not owner, or `new_slot_id` does not exist); 409 `SLOT_UNAVAILABLE` (target booked/blocked/started/out of window/same slot/other doctor); 409 `CHANGE_WINDOW_CLOSED`; 409 `INVALID_APPOINTMENT_STATE`; 422.

### API-26 POST /api/appointments/{appointment_id}/status
- Story: E3-S5 (AC-08). Auth: DOCTOR (the appointment's own doctor; another doctor 404; patient 403; admin 403).
- Body: `{ "status": "CHECKED_IN" | "IN_PROGRESS" | "COMPLETED" | "NO_SHOW" | "CANCELLED" | "BOOKED" }` (any enum member is syntactically valid so the state machine, not the schema, reports illegal moves).
- Allowed transitions: `BOOKED -> CHECKED_IN | CANCELLED | NO_SHOW`; `CHECKED_IN -> IN_PROGRESS | NO_SHOW`; `IN_PROGRESS -> COMPLETED`. `NO_SHOW` only when `now >= start_time` and leaves the slot BOOKED. `status: CANCELLED` from BOOKED behaves exactly like API-24 as DOCTOR (slot BLOCKED, refund once). Everything else is 409. Each valid transition appends exactly one event (`actor_role` DOCTOR).
- 200: `Appointment`.
- Errors: 401; 403; 404; 409 `INVALID_APPOINTMENT_STATE` (no event written, status unchanged); 422 (unknown status string).

### API-27 POST /api/appointments/{appointment_id}/notes
- Story: E4-S1. Auth: DOCTOR (the appointment's own doctor; another doctor 404; patient 403; admin 403).
- Body: `{ "text": string }` 1..5000 characters (counted as Unicode characters; whitespace-only is rejected as empty).
- Requires status `COMPLETED`. Append-only; multiple notes allowed. Logs only `appointment_id` and `user_id`.
- 201: `ConsultationNote`.
- Errors: 401; 403; 404; 409 `INVALID_APPOINTMENT_STATE`; 422.

### API-28 GET /api/appointments/{appointment_id}/notes
- Story: E4-S1. Auth: PATIENT (own appointment), DOCTOR (own), ADMIN (any).
- 200: `{ "items": [ConsultationNote], "total": n }` in creation order (ascending `note_id`).
- Errors: 401; 404 (other patient / other doctor / missing).

### API-29 GET /api/appointments/{appointment_id}/notes/{note_id}
- Story: E4-S1. Auth same as API-28.
- 200: `ConsultationNote`. Errors: 401; 404.
- **PUT, PATCH and DELETE on this path return 405 `METHOD_NOT_ALLOWED`** with `Allow: GET` (notes are immutable; a DB trigger independently blocks UPDATE/DELETE).

---

## 7. Endpoint summary

| ID | Method | Path | Auth | Story |
|---|---|---|---|---|
| API-01 | GET | /health | Public | E1-S2 |
| API-02 | GET | /api/config | Public | E5-S1 |
| API-03 | POST | /api/auth/register | Public | E1-S3 |
| API-04 | POST | /api/auth/login | Public | E1-S3 |
| API-05 | GET | /api/auth/me | Any | E1-S4 |
| API-06 | GET | /api/patients/me/profile | PATIENT | E1-S5 |
| API-07 | PUT | /api/patients/me/profile | PATIENT | E1-S5 |
| API-08 | GET | /api/patients/{patient_id}/profile | PATIENT(own)/ADMIN | E1-S5 |
| API-09 | GET | /api/doctors | Any | E2-S4 |
| API-10 | GET | /api/doctors/{doctor_id} | Any | E2-S4 |
| API-11 | GET | /api/doctors/{doctor_id}/slots | Any | E2-S4 |
| API-12 | GET | /api/doctors/me/slots | DOCTOR | E2-S3 |
| API-13 | PUT | /api/doctors/me/slots/{slot_id}/block | DOCTOR | E2-S3 |
| API-14 | PUT | /api/doctors/me/slots/{slot_id}/unblock | DOCTOR | E2-S3 |
| API-15 | GET | /api/doctors/me/queue | DOCTOR | E3-S5 |
| API-16 | POST | /api/admin/doctors | ADMIN | E2-S2 |
| API-17 | GET | /api/admin/users | ADMIN | E4-S2 |
| API-18 | PUT | /api/admin/users/{user_id}/deactivate | ADMIN | E4-S2 |
| API-19 | PUT | /api/admin/users/{user_id}/reactivate | ADMIN | E4-S2 |
| API-20 | PUT | /api/admin/patients/{patient_id}/profile | ADMIN | E4-S2 |
| API-21 | POST | /api/appointments | PATIENT | E3-S2 |
| API-22 | GET | /api/appointments/mine | PATIENT | E4-S3 |
| API-23 | GET | /api/appointments/{appointment_id} | PATIENT/DOCTOR/ADMIN (scoped) | E4-S3 |
| API-24 | POST | /api/appointments/{appointment_id}/cancel | PATIENT/DOCTOR (scoped) | E3-S3 |
| API-25 | POST | /api/appointments/{appointment_id}/reschedule | PATIENT | E3-S4 |
| API-26 | POST | /api/appointments/{appointment_id}/status | DOCTOR | E3-S5 |
| API-27 | POST | /api/appointments/{appointment_id}/notes | DOCTOR | E4-S1 |
| API-28 | GET | /api/appointments/{appointment_id}/notes | PATIENT/DOCTOR/ADMIN (scoped) | E4-S1 |
| API-29 | GET | /api/appointments/{appointment_id}/notes/{note_id} | PATIENT/DOCTOR/ADMIN (scoped) | E4-S1 |

## 8. Naming alignment with features.json and stories
`features.json`, `specs/features.json` and `specs/stories/*.md` now use snake_case for every API identifier (`user_id`, `doctor_id`, `appointment_id`, `slot_id`, `note_id`, `earliest_slot`, `access_token`), matching this document; the earlier camelCase mentions (`userId`, `doctorId`, `appointmentId`, `earliestSlot`) were rewritten and no longer deviate. Browser/tool API names that are not part of this contract (`sessionStorage`, `localStorage`, `scrollWidth`, `timezoneId`) intentionally keep their own spelling. Registration and profile fields are `full_name`, `age` (integer), `gender` and `phone` (AC-01); there is no `date_of_birth`.
