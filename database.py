"""
database.py - Oracle PL/SQL Database Integration Module for MCA Dual Quiz App.
Handles all database operations via Oracle PL/SQL packages, procedures, and functions.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import oracledb


def load_env_file(filepath: Optional[str] = None) -> None:
    """
    Parse a local .env file and load variables into os.environ if not already set.
    Avoids requiring third-party python-dotenv package.
    """
    if filepath is None:
        filepath = Path(__file__).resolve().parent / ".env"
    else:
        filepath = Path(filepath)

    if not filepath.is_file():
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = val
    except Exception as e:
        print(f"[database.py] Warning loading .env: {e}")


# Load environment variables on module import
load_env_file()


def get_db_config() -> Dict[str, Any]:
    """Retrieve Oracle DB connection settings from environment or defaults."""
    return {
        "user": os.environ.get("ORACLE_USER", "system"),
        "password": os.environ.get("ORACLE_PASSWORD", ""),
        "host": os.environ.get("ORACLE_HOST", "localhost"),
        "port": int(os.environ.get("ORACLE_PORT", 1521)),
        "service_name": os.environ.get("ORACLE_SERVICE", "FREEPDB1"),
        "default_student": os.environ.get("DEFAULT_STUDENT", "Student"),
    }


def get_connection():
    """
    Establish and return a connection to the Oracle Database.
    Raises oracledb.Error on failure.
    """
    config = get_db_config()

    if not config["password"]:
        raise ValueError(
            "Oracle password is not set in .env. Please configure ORACLE_PASSWORD in .env."
        )

    # In modern oracledb (thin mode, default), connect using tcp connection
    dsn = f"{config['host']}:{config['port']}/{config['service_name']}"
    return oracledb.connect(
        user=config["user"],
        password=config["password"],
        dsn=dsn
    )


def test_connection() -> Tuple[bool, str]:
    """
    Test the Oracle connection and check if PL/SQL package exists.
    Returns: (success: bool, message: str)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT banner FROM v$version WHERE ROWNUM = 1")
        row = cursor.fetchone()
        version = row[0] if row else "Oracle Database"

        # Check if PKG_QUIZ_MANAGER exists
        cursor.execute(
            "SELECT object_name FROM user_objects WHERE object_name = 'PKG_QUIZ_MANAGER' AND object_type = 'PACKAGE'"
        )
        pkg_row = cursor.fetchone()
        cursor.close()

        if pkg_row:
            return True, f"Connected to {version}\nPKG_QUIZ_MANAGER package verified."
        else:
            return True, f"Connected to {version}\nWarning: PKG_QUIZ_MANAGER not found. Please run database_setup.sql."
    except Exception as ex:
        return False, str(ex)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


# ============================================================================
# PL/SQL OPERATIONS
# ============================================================================

def get_subjects() -> List[Dict[str, Any]]:
    """
    Calls PKG_QUIZ_MANAGER.SP_GET_SUBJECTS to retrieve available subjects.
    Returns: List of subject dicts: [{"subject_id", "subject_name", "description", "question_count"}]
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ref_cur = cursor.var(oracledb.DB_TYPE_CURSOR)
        cursor.callproc("PKG_QUIZ_MANAGER.SP_GET_SUBJECTS", [ref_cur])

        result_cur = ref_cur.getvalue()
        subjects = []
        for row in result_cur.fetchall():
            subjects.append({
                "subject_id": row[0],
                "subject_name": row[1],
                "description": row[2] or "",
                "question_count": row[3] or 0
            })
        result_cur.close()
        cursor.close()
        return subjects
    except Exception as ex:
        print(f"[database.py] get_subjects error: {ex}")
        raise
    finally:
        if conn:
            conn.close()


def get_questions_by_subject(subject_name: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Calls PKG_QUIZ_MANAGER.SP_GET_QUESTIONS_BY_SUBJECT to fetch randomized questions.
    Returns: List of question dicts matching Tkinter app format.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ref_cur = cursor.var(oracledb.DB_TYPE_CURSOR)
        cursor.callproc(
            "PKG_QUIZ_MANAGER.SP_GET_QUESTIONS_BY_SUBJECT",
            [subject_name, limit, ref_cur]
        )

        result_cur = ref_cur.getvalue()
        questions = []
        for row in result_cur.fetchall():
            questions.append({
                "id": row[0],
                "question": row[1],
                "options": [row[2], row[3], row[4], row[5]],
                "answer": row[6]
            })
        result_cur.close()
        cursor.close()
        return questions
    except Exception as ex:
        print(f"[database.py] get_questions_by_subject error: {ex}")
        raise
    finally:
        if conn:
            conn.close()


def check_answer(question_id: int, selected_option: str) -> bool:
    """
    Calls PL/SQL function PKG_QUIZ_MANAGER.FN_CHECK_ANSWER to verify answer.
    Returns: True if correct, False otherwise.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        is_correct = cursor.callfunc(
            "PKG_QUIZ_MANAGER.FN_CHECK_ANSWER",
            oracledb.NUMBER,
            [question_id, selected_option]
        )
        cursor.close()
        return bool(is_correct == 1)
    except Exception as ex:
        print(f"[database.py] check_answer error: {ex}")
        raise
    finally:
        if conn:
            conn.close()


def save_full_quiz_result(
    username: str,
    subject_name: str,
    score: int,
    total_questions: int,
    responses: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Saves attempt and all question responses through PL/SQL procedures.
    Uses PKG_QUIZ_MANAGER.SP_SAVE_QUIZ_ATTEMPT and PKG_QUIZ_MANAGER.SP_RECORD_QUIZ_RESPONSE.
    Returns: {"attempt_id", "percentage", "performance_message"}
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        p_attempt_id = cursor.var(oracledb.NUMBER)
        p_percentage = cursor.var(oracledb.NUMBER)
        p_perf_msg = cursor.var(oracledb.STRING)

        cursor.callproc(
            "PKG_QUIZ_MANAGER.SP_SAVE_QUIZ_ATTEMPT",
            [
                username,
                subject_name,
                score,
                total_questions,
                p_attempt_id,
                p_percentage,
                p_perf_msg
            ]
        )

        attempt_id = int(p_attempt_id.getvalue())
        percentage = float(p_percentage.getvalue())
        perf_msg = str(p_perf_msg.getvalue())

        # Record each individual response
        for item in responses:
            q_id = item["question_id"]
            selected_opt = item["selected_option"]
            p_correct = cursor.var(oracledb.NUMBER)

            cursor.callproc(
                "PKG_QUIZ_MANAGER.SP_RECORD_QUIZ_RESPONSE",
                [attempt_id, q_id, selected_opt, p_correct]
            )

        conn.commit()
        cursor.close()

        return {
            "attempt_id": attempt_id,
            "percentage": percentage,
            "performance_message": perf_msg
        }
    except Exception as ex:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        print(f"[database.py] save_full_quiz_result error: {ex}")
        raise
    finally:
        if conn:
            conn.close()


def get_quiz_history(username: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Calls PKG_QUIZ_MANAGER.SP_GET_USER_HISTORY to fetch previous attempts.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ref_cur = cursor.var(oracledb.DB_TYPE_CURSOR)
        cursor.callproc("PKG_QUIZ_MANAGER.SP_GET_USER_HISTORY", [username, limit, ref_cur])

        result_cur = ref_cur.getvalue()
        history = []
        for row in result_cur.fetchall():
            history.append({
                "attempt_id": row[0],
                "username": row[1] or "Anonymous",
                "subject_name": row[2],
                "score": row[3],
                "total_questions": row[4],
                "percentage": float(row[5]),
                "performance_message": row[6],
                "attempt_time": row[7]
            })
        result_cur.close()
        cursor.close()
        return history
    except Exception as ex:
        print(f"[database.py] get_quiz_history error: {ex}")
        raise
    finally:
        if conn:
            conn.close()


def get_subject_performance() -> List[Dict[str, Any]]:
    """
    Calls PKG_QUIZ_MANAGER.SP_GET_SUBJECT_PERFORMANCE to fetch statistics.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ref_cur = cursor.var(oracledb.DB_TYPE_CURSOR)
        cursor.callproc("PKG_QUIZ_MANAGER.SP_GET_SUBJECT_PERFORMANCE", [ref_cur])

        result_cur = ref_cur.getvalue()
        stats = []
        for row in result_cur.fetchall():
            stats.append({
                "subject_name": row[0],
                "total_attempts": row[1] or 0,
                "avg_percentage": float(row[2] or 0),
                "highest_score": row[3] or 0,
                "total_questions": row[4] or 0
            })
        result_cur.close()
        cursor.close()
        return stats
    except Exception as ex:
        print(f"[database.py] get_subject_performance error: {ex}")
        raise
    finally:
        if conn:
            conn.close()


def get_highest_score(subject_name: str) -> int:
    """Calls PKG_QUIZ_MANAGER.FN_GET_HIGHEST_SCORE."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        val = cursor.callfunc(
            "PKG_QUIZ_MANAGER.FN_GET_HIGHEST_SCORE",
            oracledb.NUMBER,
            [subject_name]
        )
        cursor.close()
        return int(val or 0)
    finally:
        if conn:
            conn.close()


def count_questions(subject_name: Optional[str] = None) -> int:
    """Calls PKG_QUIZ_MANAGER.FN_COUNT_QUESTIONS."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        val = cursor.callfunc(
            "PKG_QUIZ_MANAGER.FN_COUNT_QUESTIONS",
            oracledb.NUMBER,
            [subject_name]
        )
        cursor.close()
        return int(val or 0)
    finally:
        if conn:
            conn.close()


def count_attempts(subject_name: Optional[str] = None) -> int:
    """Calls PKG_QUIZ_MANAGER.FN_COUNT_ATTEMPTS."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        val = cursor.callfunc(
            "PKG_QUIZ_MANAGER.FN_COUNT_ATTEMPTS",
            oracledb.NUMBER,
            [subject_name]
        )
        cursor.close()
        return int(val or 0)
    finally:
        if conn:
            conn.close()


def add_question(
    subject_name: str,
    question_text: str,
    opt_a: str,
    opt_b: str,
    opt_c: str,
    opt_d: str,
    correct_ans: str
) -> int:
    """Calls PKG_QUIZ_MANAGER.SP_ADD_QUESTION."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        p_qid = cursor.var(oracledb.NUMBER)
        cursor.callproc(
            "PKG_QUIZ_MANAGER.SP_ADD_QUESTION",
            [subject_name, question_text, opt_a, opt_b, opt_c, opt_d, correct_ans, p_qid]
        )
        conn.commit()
        qid = int(p_qid.getvalue())
        cursor.close()
        return qid
    finally:
        if conn:
            conn.close()


def update_question(
    question_id: int,
    question_text: str,
    opt_a: str,
    opt_b: str,
    opt_c: str,
    opt_d: str,
    correct_ans: str
) -> None:
    """Calls PKG_QUIZ_MANAGER.SP_UPDATE_QUESTION."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.callproc(
            "PKG_QUIZ_MANAGER.SP_UPDATE_QUESTION",
            [question_id, question_text, opt_a, opt_b, opt_c, opt_d, correct_ans]
        )
        conn.commit()
        cursor.close()
    finally:
        if conn:
            conn.close()


def delete_question(question_id: int) -> None:
    """Calls PKG_QUIZ_MANAGER.SP_DELETE_QUESTION."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.callproc("PKG_QUIZ_MANAGER.SP_DELETE_QUESTION", [question_id])
        conn.commit()
        cursor.close()
    finally:
        if conn:
            conn.close()
