# Project Retrospective — Lab Equipment Booking System

## 1. Executive Summary

The Lab Equipment Booking System was completed as part of the University Software Engineering mini-project. The system delivers a full-stack web application built on Flask, Flask-SQLAlchemy, Flask-Login, Jinja2, and SQLite, supported by an automated test suite comprising **198 unit and integration tests** achieving **98% line coverage**, verified by Continuous Integration (GitHub Actions) and Ruff code quality checks.

---

## 2. Team Members & Module Allocations

| Team Member | GitHub Handle | Module Allocation | Key Deliverables |
|---|---|---|---|
| **Ashan Eranga** | `@ashan2k02` | **M1: FR-00 Accounts & Authentication** | Registration, login, logout, password hashing (scrypt/Werkzeug), role-based session access, coordinator role |
| **Viboothi Balasooriya** | `@ViboothiBalasooriya` | **M2: FR-01 Equipment Catalogue & M5: Approval** | Equipment CRUD, category filtering, availability management, CI/GitHub Actions setup |
| **M D S Salakshana** | `@shashisalakshana` | **M3: FR-02 Booking Requests** | Booking model, request submission, ownership tracking, pending status lifecycle, review lead |
| **Maleesha Rajanayaka** | `@MaleeshaRajanayaka` | **M4: FR-03 Booking Validation & Testing** | EP/BVA boundary validations, overlap collision logic, testing suite, QA lead |

---

## 3. Project Metrics Summary

| Metric | Target / Requirement | Final Verified Result | Status |
|---|---|---|---|
| **Total Automated Tests** | > 20 tests | **198 tests** (0 failed, 0 skipped) | Exceeded |
| **Code Coverage** | >= 40% line coverage | **98% line coverage** (12 lines missed out of 586) | Exceeded |
| **Ruff Linter Violations** | 0 violations | **0 violations** (`ruff check .` passing) | Compliant |
| **Ruff Code Formatting** | 100% formatted | **100% formatted** (`ruff format --check .` passing) | Compliant |
| **Continuous Integration** | Passing workflow | **GitHub Actions Python CI** configured | Verified |
| **Functional Modules** | FR-00, FR-01, FR-02, FR-03, FR-04 | **All 5 modules fully implemented & verified** | 100% Complete |

---

## 4. Key Pull Request & Git Integration History

The team maintained a branch-per-feature workflow with peer review before merging into `Development`:

- **PR #43, #46, #47, #48, #49, #51, #52, #53**: FR-00 User registration, login/logout, password hashing, role restrictions, and auth tests.
- **PR #54**: FR-02 Booking request model, submission form, and initial Pending lifecycle.
- **PR #56, #57**: FR-03 Booking validation rules, Equivalence Partitioning (EP), and Boundary Value Analysis (BVA).
- **PR #58, #60**: FR-01 Equipment catalogue listing, category filtering, staff addition, editing, and deletion.
- **PR #55, #63**: FR-04 Staff pending bookings view, accept/approve actions, decline/reject with reasons, and student status views.
- **PR #59**: UI modernization, clean solid theme, and responsive navigation.
- **PR #61, #62**: CI workflow fixes and automated test runner stabilization.

---

## 5. Technical Challenges and Solutions

### 5.1 Strict Booking Collision & Overlap Validation
- **Challenge:** Detecting collisions across diverse intervals (exact duplicates, partial overlaps, fully contained bookings, and envelopes) while allowing adjacent bookings (where booking B starts exactly when booking A ends).
- **Solution:** Implemented strict interval logic: an overlap exists if and only if `existing.start_time < requested.end_time` and `existing.end_time > requested.start_time`. This was verified with comprehensive Equivalence Partitioning and Boundary Value Analysis tests.

### 5.2 Role-Based Segregation and Defense-in-Depth
- **Challenge:** Preventing privilege escalation where students could access staff management routes or manipulate HTTP POST parameters to modify booking statuses or roles.
- **Solution:** Enforced server-side decorators (`@login_required`, role-checking helper), excluded role fields from registration forms, verified user ownership on private booking views, and filtered UI navigation items dynamically based on the authenticated user's role.

### 5.3 Database Integrity and Error Handling
- **Challenge:** Preventing orphan records and uncommitted session states upon validation failure or database errors.
- **Solution:** Enforced `db.session.rollback()` in all exception handlers and validated inputs prior to interacting with the database session, confirmed by automated transaction failure tests.

---

## 6. What Went Well

1. **High Test Coverage and Automation:** Building comprehensive unit and integration tests from day one allowed rapid refactoring with zero regressions.
2. **Effective Equivalence Partitioning:** Formalizing EP and BVA tables in `TESTING.md` provided unambiguous test specifications for edge cases like 29-minute bookings (rejected) vs 30-minute bookings (accepted).
3. **Automated Linting and Style Enforcement:** Ruff integration ensured consistent formatting, clean imports, and zero lint warnings across all team members' contributions.

---

## 7. Areas for Future Improvement

1. **Database-Level Concurrency Locks:** While application-level validation handles overlapping checks effectively, high-concurrency production deployments would benefit from database-level exclusion constraints or serializable transaction isolation.
2. **Notification Subsystem:** Adding automated email or in-app alerts when a booking status changes from Pending to Approved or Rejected.
3. **Recurring & Multi-Day Bookings:** Extending the booking model to accommodate recurring lab sessions and multi-day research reservations.
# RETROSPECTIVE.md

## What went well?
- The team followed the full workflow: Issue, branch, implementation, test, pull request, review, CI, merge.
- Automated tests (pytest) and Ruff in GitHub Actions caught problems before merging.
- Booking validation rules (FR-03) were tested with Equivalence Partitioning and Boundary Value Analysis.
- Splitting work into modules (accounts, equipment, booking, validation, approval) let members work in parallel.

## What caused difficulties?
- Merge conflicts in shared files (`app/__init__.py`, `app/models.py`, templates) when several branches changed them.
- Overlapping work on the equipment feature led to duplicated template blocks and a failing CI test job that needed a fix.
- Some members were new to Git branching, so early commits and pull requests needed guidance.

## What would our group do differently next time?
- Agree on shared files (models, base template) at the start and merge into `Development` more often.
- Create issues and assign owners before coding so two people do not build the same feature.
- Keep pull requests small and review them the same day.
- Write test cases for each rule before implementing it.

## Metrics
| Metric | Value |
|---|---|
| Issues completed | 36 |
| Pull requests merged | 27 |
| Peer reviews performed | 27 |
| Final test coverage | 97% (156 tests passing) |
