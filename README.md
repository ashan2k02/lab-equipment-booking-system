# Lab Equipment Booking System

## Project Description

The Lab Equipment Booking System is a web-based application developed to manage laboratory equipment bookings. It allows students to view available equipment and request bookings, while laboratory staff can manage equipment and approve or reject booking requests.

The system aims to prevent double bookings, maintain booking records, and simplify equipment availability management.

## Project Structure

The project is organized into the following main components:

Lab-Equipment-Booking-System/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   └── auth.py
├── tests/
│   └── test_basic.py
├── .github/
│   └── workflows/
│       └── ci.yml
├── run.py
├── requirements.txt
├── README.md
├── REVIEW_CHECKLIST.md
├── TESTING.md
├── RETROSPECTIVE.md
└── .gitignore

## Team Members and Module Allocation

| Team Member          | GitHub Username      | Module Allocation                                     |
| -------------------- | -------------------- | ------------------------------------------------------|
| Ashan Eranga         | @ashan2k02           | M1 – Accounts and Authentication                      |
| Viboothi Balasooriya | @ViboothiBalasooriya | M2 – Equipment Catalogue and M5 – Approval and Status |
| Shasi Salakshana     | @shashisalakshana    | M3 – Booking Requests                                 |
| Maleesha Rajanayaka  | @MaleeshaRajanayaka  | M4 – Booking Validation and Testing                   |

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

### 3. Shasi Salakshana – Booking Requests and Approval

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

| Coordination Role | Assigned Member      | Responsibilities                                         |
| ----------------- | -------------------- | -------------------------------------------------------- |
| Coordinator       | Ashan Eranga         | Organizes GitHub Issues and maintains the project board. |
| GitHub/CI Lead    | Viboothi Balasooriya | Maintains repository setup and the CI workflow.          |
| Review Lead       | Shasi Salakshana     | Coordinates peer reviews and review evidence.            |
| QA Lead           | Maleesha Rajanayaka  | Coordinates testing and maintains TESTING.md.            |

## Shared Team Responsibilities

All team members are expected to:

- Contribute to the application source code.
- Write or contribute to automated tests.
- Work through feature branches and pull requests.
- Review code written by other team members.
- Participate in integration, debugging, and testing.
- Understand and explain their own contributions during the individual viva.

## Technology Stack

- Programming Language: Python 3.11 or newer
- Web Framework: Flask
- Database: SQLite
- ORM: Flask-SQLAlchemy
- Frontend: Jinja2, HTML, and CSS
- Authentication: Flask-Login or a Flask-based implementation
- Testing: pytest and pytest-cov
- Linting: Ruff
- Version Control: Git and GitHub
- Continuous Integration: GitHub Actions

## Installation and Setup

### Prerequisites

- Python 3.11 or newer
- Git

### 1. Clone the Repository
```
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd Lab-Equipment-Booking-System
```

### 2. Create and Activate a Virtual Environment
```
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```
pip install -r requirements.txt
```

### 4. Run the Application
```
python run.py
```

Open `http://127.0.0.1:5000` in your browser.

### 5. Run Automated Tests
```
pytest
```

### 6. Run Tests with Coverage
```
pytest --cov=app --cov-report=term-missing
```

**Note:** The run and test instructions assume that `requirements.txt`, `run.py`, and the application configuration are implemented as described. Update these instructions if the actual repository structure differs.
