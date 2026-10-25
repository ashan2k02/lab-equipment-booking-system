# Lab Equipment Booking System

## Project Description

The Lab Equipment Booking System is a web-based application developed to manage laboratory equipment bookings. It allows students to view available equipment and request bookings, while laboratory staff can manage equipment and approve or reject booking requests.

The system aims to prevent double bookings, maintain booking records, and simplify equipment availability management.

## Project Structure

```text
Lab-Equipment-Booking-System/
├── app/
│   ├── __init__.py
│   ├── auth.py
│   ├── bookings.py
│   ├── equipment.py
│   ├── models.py
│   ├── static/
│   │   └── css/
│   └── templates/
│       ├── auth/
│       ├── bookings/
│       ├── equipment/
│       ├── errors/
│       ├── base.html
│       └── home.html
├── tests/
│   ├── test_app.py
│   ├── test_auth.py
│   ├── test_authentication_suite.py
│   ├── test_booking_integration.py
│   ├── test_booking_request.py
│   ├── test_equipment.py
│   ├── test_models.py
│   ├── test_password_hashing.py
│   └── test_pending_bookings.py
├── .github/
│   └── workflows/
│       └── ci.yml
├── config.py
├── seed_equipment.py
├── run.py
├── requirements.txt
├── README.md
├── REVIEW_CHECKLIST.md
├── TESTING.md
├── RETROSPECTIVE.md
└── .gitignore
```

## Team Members and Module Allocation

| Team Member | GitHub Username | Module Allocation |
|---|---|---|
| Ashan Eranga | @ashan2k02 | M1 – Accounts and Authentication |
| Viboothi Balasooriya | @ViboothiBalasooriya | M2 – Equipment Catalogue and M5 – Approval and Status|
| M D S Salakshana | @shashisalakshana | M3 – Booking Requests  |
| Maleesha Rajanayaka | @MaleeshaRajanayaka | M4 – Booking Validation and Testing |

## Individual Responsibilities

### 1. Ashan Eranga – Accounts and Authentication

- Implement student registration, login, and logout.
- Implement password hashing.
- Enforce student and staff role restrictions.
- Coordinate GitHub Issues and the project board.

### 2. Viboothi Balasooriya – Equipment Catalogue

- Implement equipment listing and category filtering.
- Implement equipment creation, editing, and deletion for staff.
- Manage equipment status, including Available and Out of service.
- Configure and maintain the GitHub Actions CI workflow.

### 3. Shashi Salakshana – Booking Requests and Approval

- Implement the booking request form and booking model.
- Handle booking date, start time, and end time inputs.
- Implement staff approval and rejection functionality.
- Display booking statuses to students.
- Coordinate pull request reviews.

### 4. Maleesha Rajanayaka – Booking Validation and Testing

- Implement booking duration validation.
- Prevent bookings that start in the past.
- Prevent bookings for equipment that is out of service.
- Implement overlapping booking validation.
- Develop automated tests using pytest.
- Maintain TESTING.md and coordinate test coverage.

## Coordination Roles

| Coordination Role | Assigned Member | Responsibilities |
|---|---|---|
| Coordinator | Ashan Eranga | Organizes GitHub Issues and maintains the project board. |
| GitHub/CI Lead | Viboothi Balasooriya | Maintains repository setup and the CI workflow. |
| Review Lead | Shashi Salakshana | Coordinates peer reviews and review evidence. |
| QA Lead | Maleesha Rajanayaka | Coordinates testing and maintains TESTING.md. |

## Shared Team Responsibilities

All team members are expected to:

- Contribute to the application source code.
- Write or contribute to automated tests.
- Work through feature branches and pull requests.
- Review code written by other team members.
- Participate in integration, debugging, and testing.
- Understand and explain their own contributions during the individual viva.

## Functional Requirements

### FR-00 – Accounts and Login

- Students can register, log in, and log out.
- Public registration creates Student accounts only.
- Staff accounts are created using a documented setup method.
- Passwords are stored securely using password hashing.
- Students cannot access staff-only pages.

### FR-01 – Equipment Catalogue

- Staff can add, edit, and delete equipment.
- Each item contains a name, category, description, and status.
- Equipment status is either Available or Out of service.
- Logged-in users can view and filter equipment by category.

### FR-02 – Request a Booking

- Students can select equipment, a booking date, a start time, and an end time.
- New valid booking requests are initially assigned Pending status.

### FR-03 – Booking Validation

- The end time must be later than the start time.
- Booking duration must be at least 30 minutes and no more than 4 hours.
- Bookings cannot start in the past.
- Equipment marked Out of service cannot be booked.
- Overlapping Pending or Approved bookings for the same equipment are rejected.
- A booking can start exactly when an existing booking ends.

### FR-04 – Booking Approval and Status

- Staff can view Pending booking requests.
- Staff can approve or reject requests.
- Staff may provide a rejection reason.
- Students can view their own booking requests and statuses.

## Technology Stack

- **Programming Language:** Python 3.11 or newer
- **Web Framework:** Flask
- **Database:** SQLite
- **ORM:** Flask-SQLAlchemy
- **Frontend:** Jinja2, HTML, and CSS
- **Authentication:** Flask-Login or a Flask-based implementation
- **Testing:** pytest and pytest-cov
- **Linting:** Ruff
- **Version Control:** Git and GitHub
- **Continuous Integration:** GitHub Actions

## Installation and Setup

### Prerequisites

- Python 3.11 or newer
- Git
- A GitHub account

### 1. Clone the Repository

Replace the placeholder with the actual repository URL.

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd Lab-Equipment-Booking-System
```

### 2. Create a Virtual Environment

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Database Setup and Seeding (Optional)

To seed initial lab equipment items and a default Staff account:

```bash
python seed_equipment.py
```

Default seeded credentials:
- **Staff account:** `lab_staff` / `StaffPassword123!` (email: `lab.staff@local.test`)
- *Note:* Students can register directly via the **Register** page on the web application.

### 5. Run the Application

```bash
python run.py
```

Open the following URL in your browser:

http://127.0.0.1:5000

### 6. Run Automated Tests

```bash
pytest
```

### 7. Run Tests with Coverage

```bash
pytest --cov=app --cov-report=term-missing
```

### 8. Run Ruff Linter and Formatter

```bash
ruff check .
ruff format --check .
```

## GitHub Workflow

The project follows this development workflow:

**Issue → Branch → Implementation → Test → Pull Request → Review → CI → Merge**

- Create or identify a GitHub Issue before starting a task.
- Create a feature branch for the implementation.
- Write code and relevant automated tests.
- Commit changes with meaningful commit messages.
- Open a pull request and reference the related Issue.
- Request a review from another team member.
- Ensure automated CI checks pass before merging.
- Do not approve your own pull request.

## Testing and Code Quality

The project uses pytest for automated testing, pytest-cov for measuring test coverage, and Ruff for Python linting.

Testing focuses on the main functional requirements, especially booking validation rules such as booking duration, past dates, equipment availability, and overlapping bookings.

The final project aims for at least 40% line coverage, as specified in the assignment.

## Project Documentation

The repository includes the following project documentation:

- **README.md** – Project overview, team responsibilities, installation, and usage instructions.
- **TESTING.md** – Test design, test cases, and testing results.
- **REVIEW_CHECKLIST.md** – Checklist used during code reviews.
- **RETROSPECTIVE.md** – Summary of lessons learned and project metrics.

## Project Evaluation

The project is evaluated in three stages:

- **E1 – Setup Check:** Repository, project board, basic application setup, CI, and review checklist.
- **E2 – Intermediate Review:** Core features, booking validation progress, tests, and peer-reviewed pull requests.
- **E3 – Final Evaluation:** Complete functionality, automated testing, coverage, CI, documentation, and individual viva.

## Academic Integrity and Individual Contribution

All team members are responsible for understanding the code they contribute. Each member must participate in implementation, testing, pull requests, and peer reviews, and be able to explain their contribution during the individual viva.

---

**Note:** The project structure and commands above describe the intended setup. Update them if the actual repository structure or implementation differs.
