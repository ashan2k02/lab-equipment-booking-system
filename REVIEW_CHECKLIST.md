# Code Review Checklist

This checklist must be applied by peer reviewers when reviewing Pull Requests. Reviewers must verify each item and leave evidence of review on the pull request before approval and merging.

- [ ] User inputs are validated.
- [ ] Business rules and conditions are correct.
- [ ] Database operations are appropriate.
- [ ] Login and role restrictions are checked.
- [ ] Errors are handled appropriately.
- [ ] No passwords or secret values are committed.
- [ ] Relevant automated tests have been added.
- [ ] Existing tests still pass.

---

### Review Guidelines for Functional Modules

- **FR-00 (Accounts and Authentication):**
  - Verify inputs (username, email, password length, format) are validated on the server side.
  - Verify passwords are never logged, displayed, or stored in plaintext (always hashed).
  - Verify public registration assigns only the `Student` role and cannot be manipulated to create staff accounts.
  - Verify database operations (such as duplicate checks and inserts) handle rollbacks safely upon error.
  - Verify automated tests cover successful paths, boundary validations, duplicate prevention, and role restrictions.
- **FR-01 to FR-04 (Equipment & Bookings):**
  - Verify staff-only operations require staff role checks.
  - Verify booking validation rules (duration, start/end time, overlapping checks, past date prevention) are enforced.
