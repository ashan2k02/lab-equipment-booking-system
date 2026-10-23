# Testing Guide

## 1. Purpose and scope

This guide records the automated testing approach for the Lab Equipment Booking System, with emphasis on FR-03 booking validation. The booking-request tests exercise validation before a `Booking` is added to the database and verify both accepted and rejected HTTP flows.

The main FR-03 tests are in `tests/test_booking_request.py`. Integration coverage for booking submission, required fields, initial Pending status, and authentication is in `tests/test_booking_integration.py`. FR-04 approval, rejection, persistence, authorization, and invalid-action coverage is in `tests/test_pending_bookings.py`.

## 2. Testing tools and environment

- Python with Flask, Flask-SQLAlchemy, Flask-Login, and SQLite.
- `pytest` and `pytest-cov` for automated tests.
- `ruff` for linting.
- Test fixtures configure SQLite in memory (`sqlite:///:memory:`), so test data is isolated from the development database.

Dependencies are listed in `requirements.txt`. This repository contains a project virtual environment at `.venv`.

## 3. How to run the test suite

From the repository root, activate the virtual environment and run:

```zsh
source .venv/bin/activate
python -m pytest
python -m ruff check .
git diff --check
```

Alternatively, run the environment's interpreter without activating it:

```zsh
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
git diff --check
```

## 4. How to run booking-specific tests

```zsh
.venv/bin/python -m pytest tests/test_booking_request.py -q
.venv/bin/python -m pytest tests/test_booking_integration.py -q
```

`test_booking_request.py` includes route-level validation, duration boundaries, equipment availability, invalid inputs, overlap scenarios, form re-rendering, and booking-detail access tests. `test_booking_integration.py` covers end-to-end booking submission, required fields, initial Pending status, status-tampering prevention, and authentication.

## 5. Booking validation rules

`validate_booking_input()` in `app/bookings.py` validates a booking before `request_booking()` calls `db.session.add()` or `db.session.commit()`.

- Equipment must be selected, parse as an ID, and exist.
- Only `Equipment.STATUS_AVAILABLE` is bookable. Out-of-service and unrecognised statuses are rejected.
- Booking date, start time, and end time are required and parsed server-side.
- Booking dates in the past and start times already passed on the current date are rejected.
- End time must be later than start time.
- Duration must be at least 30 minutes and no more than 4 hours, inclusive.
- A new request conflicts when the same equipment and date have a Pending or Approved booking where `existing.start_time < requested.end_time` and `existing.end_time > requested.start_time`.
- All new valid requests are saved with status `Pending`.
- Staff approval rechecks the existing equipment, date/time, duration, and Pending/Approved overlap rules before saving `Approved`.
- Staff rejection saves `Rejected` and an optional reason of up to 255 characters.
- Approval and rejection actions accept only bookings that are currently `Pending`.

## 6. Equivalence Partitioning

| Input area | Valid class covered | Invalid class covered |
|---|---|---|
| Required fields | Equipment, date, start time, and end time supplied | Each field missing; completely empty form |
| Equipment ID | Existing available equipment | Missing, non-numeric, and nonexistent IDs |
| Equipment status | `Available` | `Out of service` and unrecognised `Maintenance` status |
| Booking date | Today or future ISO date | Malformed date and past date |
| Booking times | Parseable start/end times with end later than start | Malformed start/end time; equal or reversed range |
| Duration | 30 minutes through 4 hours | Under 30 minutes and over 4 hours |
| Existing reservations | Different equipment/date, adjacent windows, Rejected, or Cancelled booking | Overlap with Pending or Approved booking |

## 7. Boundary Value Analysis

The following automated cases are implemented in `test_booking_request_duration_limits` and `test_booking_request_overlap_validation`.

| Boundary | Test input | Expected result |
|---|---|---|
| Below minimum | `10:00-10:29` | Rejected, HTTP 400 |
| Minimum | `10:00-10:30` | Accepted and persisted |
| Maximum | `10:00-14:00` | Accepted and persisted |
| Above maximum | `10:00-14:01` | Rejected, HTTP 400 |
| Equal endpoints | `14:00-14:00` | Rejected |
| Adjacent before | Existing `10:00-11:00`, requested `09:00-10:00` | Accepted |
| Adjacent after | Existing `10:00-11:00`, requested `11:00-12:00` | Accepted |
| Overlap | Duplicate, partial, contained, and containing intervals | Rejected, HTTP 400 |

## 8. Booking overlap test cases

Existing booking windows are created for the same date and equipment before the request is submitted.

- Pending bookings block exact duplicates, partial overlaps, contained ranges, and ranges containing the existing booking.
- Approved bookings block overlaps.
- Rejected and Cancelled bookings do not block a new overlapping request.
- A booking on a different equipment item does not conflict.
- A booking on a different date does not conflict.
- Adjacent windows are accepted because the overlap comparison is strict.

Rejected overlap tests assert the error message, HTTP 400, unchanged booking count, unchanged existing booking data, and no pending or dirty session objects. Accepted cases assert that the newly created booking is Pending.

## 9. Equipment availability test cases

- Existing available equipment is accepted by the valid booking-request tests.
- Out-of-service equipment is rejected and no `Booking` is saved.
- An equipment record with the unrecognised status `Maintenance` is rejected and no `Booking` is saved.
- Non-numeric and nonexistent equipment IDs are rejected and no `Booking` is saved.

## 10. Invalid request handling

All failed booking validation paths return HTTP 400, flash a user-facing error, and re-render `bookings/request.html`. The form receives the submitted values and the equipment list again.

Tests cover missing fields, malformed date/time values, invalid equipment IDs/statuses, past dates/times, time ordering, duration limits, and booking conflicts. Rejection tests assert no invalid `Booking` record is persisted. The form re-rendering test also checks that the session has no pending or dirty objects after a rejected request.

## 11. FR-04 booking approval and rejection tests

The FR-04 tests verify that staff can approve and reject Pending bookings, status changes persist, rejection reasons are stored, invalid booking IDs return 404, repeated actions do not overwrite a non-Pending booking, approval rechecks overlapping bookings, students and anonymous users cannot execute staff actions, and students can see persisted statuses in My Bookings.

## 12. Test execution results

Latest verified execution result for the current FR-04 implementation:

```text
164 passed, 4 warnings
```

Coverage completed at 97% overall. Ruff completed with `All checks passed!`, and `git diff --check` completed without whitespace errors.

## 13. Known warnings or limitations

- The test run emits a Flask-Login deprecation warning because its dependency uses `datetime.utcnow()`, plus SQLite resource warnings during test cleanup. These warnings are outside the FR-04 implementation.
- Overlap prevention is application-level. The tests verify normal request behavior, but no database-level constraint prevents a theoretical race between simultaneous overlapping requests.
- The documented test suite covers the listed equivalence classes and boundaries; it does not claim exhaustive coverage of every possible input or concurrent execution path.
