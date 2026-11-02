"""
test_database.py - Automated test suite for Oracle PL/SQL integration and fallback behavior.
"""

import unittest
import database


class TestOracleIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = database.get_db_config()
        cls.online, cls.status_msg = database.test_connection()
        print(f"\n[SUITE] Config: user={cls.config['user']}, host={cls.config['host']}:{cls.config['port']}, service={cls.config['service_name']}")
        print(f"[SUITE] Database Online: {cls.online}")
        if not cls.online:
            print(f"[SUITE] Connection Note: {cls.status_msg}")

    def test_01_config_loaded(self):
        """Verify configuration fields exist in .env / defaults."""
        self.assertIn("user", self.config)
        self.assertIn("host", self.config)
        self.assertIn("port", self.config)
        self.assertIn("service_name", self.config)

    def test_02_connection(self):
        """Test connection status to Oracle."""
        if not self.online:
            self.skipTest(f"Oracle DB is currently offline or credentials need updating: {self.status_msg}")

    def test_03_get_subjects(self):
        """Test SP_GET_SUBJECTS procedure."""
        if not self.online:
            self.skipTest("Oracle DB is offline.")
        subjects = database.get_subjects()
        self.assertIsInstance(subjects, list)
        self.assertGreater(len(subjects), 0)
        subject_names = [s["subject_name"] for s in subjects]
        print(f"\n[TEST 3] Found subjects: {subject_names}")
        self.assertIn("Python", subject_names)
        self.assertIn("DAA", subject_names)

    def test_04_get_questions(self):
        """Test SP_GET_QUESTIONS_BY_SUBJECT procedure."""
        if not self.online:
            self.skipTest("Oracle DB is offline.")
        q_list = database.get_questions_by_subject("Python", limit=5)
        self.assertEqual(len(q_list), 5)
        for q in q_list:
            self.assertIn("id", q)
            self.assertIn("question", q)
            self.assertEqual(len(q["options"]), 4)
            self.assertIn("answer", q)
        print(f"\n[TEST 4] Retrieved {len(q_list)} Python questions successfully.")

    def test_05_check_answer_function(self):
        """Test FN_CHECK_ANSWER PL/SQL function."""
        if not self.online:
            self.skipTest("Oracle DB is offline.")
        q_list = database.get_questions_by_subject("Python", limit=1)
        self.assertEqual(len(q_list), 1)
        target = q_list[0]
        # Test correct answer
        is_correct = database.check_answer(target["id"], target["answer"])
        self.assertTrue(is_correct)
        # Test incorrect answer
        wrong_opt = [o for o in target["options"] if o != target["answer"]][0]
        is_wrong = database.check_answer(target["id"], wrong_opt)
        self.assertFalse(is_wrong)
        print(f"\n[TEST 5] FN_CHECK_ANSWER correctly evaluated true/false.")

    def test_06_save_attempt_and_responses(self):
        """Test SP_SAVE_QUIZ_ATTEMPT and SP_RECORD_QUIZ_RESPONSE."""
        if not self.online:
            self.skipTest("Oracle DB is offline.")
        q_list = database.get_questions_by_subject("DAA", limit=2)
        responses = [
            {"question_id": q_list[0]["id"], "selected_option": q_list[0]["answer"]},
            {"question_id": q_list[1]["id"], "selected_option": "WrongOption"}
        ]
        result = database.save_full_quiz_result(
            username="TestStudent",
            subject_name="DAA",
            score=1,
            total_questions=2,
            responses=responses
        )
        self.assertIn("attempt_id", result)
        self.assertEqual(result["percentage"], 50.0)
        self.assertIn("performance_message", result)
        print(f"\n[TEST 6] Saved attempt ID #{result['attempt_id']}, percentage={result['percentage']}%, message='{result['performance_message']}'")

    def test_07_quiz_history(self):
        """Test SP_GET_USER_HISTORY procedure."""
        if not self.online:
            self.skipTest("Oracle DB is offline.")
        history = database.get_quiz_history(limit=5)
        self.assertIsInstance(history, list)
        print(f"\n[TEST 7] Retrieved {len(history)} history entries.")

    def test_08_subject_performance(self):
        """Test SP_GET_SUBJECT_PERFORMANCE procedure."""
        if not self.online:
            self.skipTest("Oracle DB is offline.")
        stats = database.get_subject_performance()
        self.assertIsInstance(stats, list)
        print(f"\n[TEST 8] Subject stats count: {len(stats)}")

    def test_09_question_crud(self):
        """Test SP_ADD_QUESTION, SP_UPDATE_QUESTION, SP_DELETE_QUESTION."""
        if not self.online:
            self.skipTest("Oracle DB is offline.")
        # Add question
        qid = database.add_question(
            subject_name="Python",
            question_text="Sample Test Question 123?",
            opt_a="A",
            opt_b="B",
            opt_c="C",
            opt_d="D",
            correct_ans="A"
        )
        self.assertIsInstance(qid, int)
        print(f"\n[TEST 9] Added question ID {qid}")

        # Update question
        database.update_question(
            question_id=qid,
            question_text="Sample Test Question 123 Updated?",
            opt_a="A",
            opt_b="B",
            opt_c="C",
            opt_d="D",
            correct_ans="B"
        )
        print(f"[TEST 9] Updated question ID {qid}")

        # Delete question
        database.delete_question(qid)
        print(f"[TEST 9] Deleted question ID {qid}")


if __name__ == "__main__":
    unittest.main()
