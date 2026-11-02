# MCA Dual Quiz Portal - Oracle PL/SQL Enhanced Edition

An enhanced **Tkinter Dual Quiz Desktop Application** integrated with **Oracle AI Database Free 26ai** and **PL/SQL**.

All core database operations—including fetching questions, validating answers, calculating percentages and performance ratings, persisting quiz attempts, recording question-level responses, and compiling performance statistics—are executed natively in Oracle via PL/SQL stored procedures and functions.

---

## 1. Project Architecture

```
MCA Quiz Project/
├── main.py              # Application entry point (MCA Quiz Portal GUI)
├── quiz_app.py          # Tkinter Quiz UI, question flow, and history viewer
├── questions.py         # Seed question bank (fallback for offline mode)
├── database.py          # Oracle connection and PL/SQL invocation module (oracledb)
├── database_setup.sql   # DDL tables, constraints, triggers, and PL/SQL package/seed data
├── test_database.py     # Automated test suite for database and PL/SQL operations
├── .env                 # Local Oracle credentials (excluded from Git)
├── .env.example         # Template for Oracle connection configuration
├── .gitignore           # Git ignore rules for credentials and cache
└── README.md            # Complete setup, execution, and architecture guide
```

---

## 2. Oracle Database Schema Design

The schema is created in `database_setup.sql` using modern Oracle 26ai features (identity columns, check constraints, foreign key cascades):

| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| **`QUIZ_SUBJECTS`** | Available subjects for quizzes | `SUBJECT_ID` (PK Identity), `SUBJECT_NAME` (Unique), `DESCRIPTION` |
| **`QUIZ_QUESTIONS`** | 4-option MCQs linked to subjects | `QUESTION_ID` (PK Identity), `SUBJECT_ID` (FK), `QUESTION_TEXT`, `OPTION_A..D`, `CORRECT_ANSWER` |
| **`QUIZ_USERS`** | Registered students / users | `USER_ID` (PK Identity), `USERNAME` (Unique), `FULL_NAME` |
| **`QUIZ_ATTEMPTS`** | Completed quiz scores & metadata | `ATTEMPT_ID` (PK Identity), `USER_ID` (FK), `SUBJECT_ID` (FK), `SCORE`, `TOTAL_QUESTIONS`, `PERCENTAGE`, `PERFORMANCE_MESSAGE`, `ATTEMPT_DATE` |
| **`QUIZ_RESPONSES`** | Granular user answers per question | `RESPONSE_ID` (PK Identity), `ATTEMPT_ID` (FK), `QUESTION_ID` (FK), `SELECTED_OPTION`, `CORRECT_OPTION`, `IS_CORRECT`, `ANSWERED_AT` |

### Database Triggers
- **`TRG_CHECK_QUESTION_OPTIONS`**: Enforces that the `CORRECT_ANSWER` must strictly match one of `OPTION_A`, `OPTION_B`, `OPTION_C`, or `OPTION_D`.
- **`TRG_ATTEMPT_TIMESTAMP`**: Automatically populates `ATTEMPT_DATE` with `CURRENT_TIMESTAMP` on each quiz attempt.

---

## 3. PL/SQL Implementation (`PKG_QUIZ_MANAGER`)

All database calculations and data access are delegated to the **`PKG_QUIZ_MANAGER`** PL/SQL package (and exposed via standalone wrappers):

### PL/SQL Functions
- **`FN_CALCULATE_PERCENTAGE(p_score, p_total)`**: Accurately computes `(score / total) * 100` rounded to 2 decimal places.
- **`FN_GET_PERFORMANCE_MSG(p_percentage)`**: Generates performance evaluations:
  - $\ge 80\%$: *"Excellent Performance!"*
  - $\ge 60\%$: *"Good Performance!"*
  - $\ge 40\%$: *"Average Performance!"*
  - $< 40\%$: *"Keep Practicing!"*
- **`FN_CHECK_ANSWER(p_question_id, p_selected_option)`**: Evaluates user submission against the database and returns `1` (correct) or `0` (incorrect).
- **`FN_COUNT_QUESTIONS(p_subject_name)`**: Counts available questions overall or per subject.
- **`FN_COUNT_ATTEMPTS(p_subject_name)`**: Counts total quiz attempts recorded.
- **`FN_GET_HIGHEST_SCORE(p_subject_name)`**: Retrieves the all-time high score for a subject.

### PL/SQL Stored Procedures
- **`SP_GET_SUBJECTS(p_cursor OUT SYS_REFCURSOR)`**: Retrieves all subjects along with their question counts.
- **`SP_GET_QUESTIONS_BY_SUBJECT(p_subject_name, p_limit, p_cursor OUT SYS_REFCURSOR)`**: Returns a random sample of questions for the selected subject using `ORDER BY DBMS_RANDOM.VALUE FETCH FIRST p_limit ROWS ONLY`.
- **`SP_SAVE_QUIZ_ATTEMPT(p_username, p_subject_name, p_score, p_total, p_attempt_id OUT, p_percentage OUT, p_perf_msg OUT)`**: Resolves or auto-creates the user, calculates score percentage and rating message in PL/SQL, records the attempt, and returns the generated `ATTEMPT_ID`.
- **`SP_RECORD_QUIZ_RESPONSE(p_attempt_id, p_question_id, p_selected_option, p_is_correct OUT)`**: Records the student's answer for each question with correctness status.
- **`SP_GET_USER_HISTORY(p_username, p_limit, p_cursor OUT SYS_REFCURSOR)`**: Fetches recent quiz attempts with score, percentage, rating, and formatted date.
- **`SP_GET_SUBJECT_PERFORMANCE(p_cursor OUT SYS_REFCURSOR)`**: Aggregates statistics per subject (total attempts, average percentage, highest score).
- **`SP_ADD_QUESTION(...)`**, **`SP_UPDATE_QUESTION(...)`**, **`SP_DELETE_QUESTION(...)`**: Stored procedures for question bank management.

---

## 4. Setup and Installation

### Step 1: Install Python Dependencies
The project uses the official **`oracledb`** driver:

```powershell
python -m pip install oracledb
```

### Step 2: Configure Oracle Credentials
Copy `.env.example` to `.env` (or edit the existing `.env`):

```ini
ORACLE_USER=system
ORACLE_PASSWORD=YourOraclePassword
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE=FREEPDB1
DEFAULT_STUDENT=Student
```

> **Note**: For Oracle Database Free 26ai / 23ai on Windows, the default Pluggable Database (PDB) service name is usually `FREEPDB1`. If connecting directly to the Container Database, use `FREE`.

---

## 5. Running the Database Setup Script

You can execute `database_setup.sql` using any of the following tools:

### Option A: Using SQL*Plus (Command Line)
1. Open Command Prompt or PowerShell.
2. Connect to your Oracle PDB:
   ```cmd
   sqlplus system/YourPassword@localhost:1521/FREEPDB1
   ```
3. Run the setup script:
   ```sql
   @database_setup.sql
   ```
4. Confirm output finishes with `Database setup and PL/SQL objects created successfully!`.

### Option B: Using Oracle SQL Developer
1. Open Oracle SQL Developer.
2. Create a connection to `localhost`, port `1521`, Service Name `FREEPDB1` using user `system`.
3. Open `database_setup.sql` (`File -> Open`).
4. Click **Run Script (F5)**.

### Option C: Using VS Code (Oracle Developer Tools extension)
1. Install **Oracle Developer Tools for VS Code**.
2. Connect to your local Oracle Database.
3. Open `database_setup.sql` in VS Code and execute as a script.

---

## 6. Running and Testing the Application

### Test Database Integration
Run the automated test suite to verify configuration, connection, and PL/SQL procedures:

```powershell
python test_database.py
```

### Launch the GUI Application
```powershell
python main.py
```

---

## 7. Features & GUI Highlights

1. **Dynamic Subject Discovery**: Subjects (`Python`, `DAA`, etc.) are queried directly from the Oracle database on startup.
2. **PL/SQL Quiz Execution**: 5 questions are fetched randomly per quiz run via `SP_GET_QUESTIONS_BY_SUBJECT`.
3. **Native PL/SQL Answer Evaluation**: Submissions are checked via `FN_CHECK_ANSWER`.
4. **Persistent Scores & Responses**: Scores, percentages, and response audits are persisted into `QUIZ_ATTEMPTS` and `QUIZ_RESPONSES`.
5. **Interactive History Window**: Click **"View Quiz History"** on the portal screen to view previous attempts and subject-wise averages/high scores.
6. **Graceful Fallback**: If the Oracle database listener is stopped or undergoing maintenance, the application alerts the user and runs seamlessly in offline mode without crashing.
