"""
quiz_app.py - Tkinter GUI and quiz flow for the Dual Quiz App.
Integrated with Oracle PL/SQL for question fetching, answer verification,
and attempt/response persistence.
"""

import tkinter as tk
from tkinter import messagebox, ttk
import random
from typing import List, Dict, Any, Optional

import database
from questions import python_questions, daa_questions


class QuizApp:

    def __init__(
        self,
        root: tk.Tk,
        subject: str,
        question_bank: Optional[List[Dict[str, Any]]] = None,
        username: str = "Student",
        on_return_home: Optional[Any] = None
    ):
        self.root = root
        self.subject = subject
        self.username = username or "Student"
        self.on_return_home = on_return_home
        self.offline_mode = False

        # Load questions from Oracle PL/SQL or fallback to local question bank
        self.questions = self.load_questions(question_bank)

        self.question_number = 0
        self.score = 0
        self.responses: List[Dict[str, Any]] = []

        self.selected_answer = tk.StringVar()

        self.create_quiz_screen()
        self.show_question()

    def load_questions(
        self,
        fallback_bank: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Loads 5 questions via Oracle PL/SQL stored procedure SP_GET_QUESTIONS_BY_SUBJECT.
        If database is unavailable, falls back to local questions.py list.
        """
        try:
            db_questions = database.get_questions_by_subject(self.subject, limit=5)
            if db_questions and len(db_questions) > 0:
                return db_questions
            else:
                print(f"[quiz_app] No questions returned from Oracle for {self.subject}, using fallback.")
        except Exception as ex:
            self.offline_mode = True
            print(f"[quiz_app] Oracle connection unavailable: {ex}. Using local question bank.")
            messagebox.showwarning(
                "Offline Mode",
                f"Could not connect to Oracle Database:\n{ex}\n\nRunning quiz in offline mode."
            )

        # Fallback to local python_questions or daa_questions
        bank = fallback_bank
        if not bank:
            if self.subject.lower() == "python":
                bank = python_questions
            elif self.subject.lower() == "daa":
                bank = daa_questions
            else:
                bank = []

        if len(bank) >= 5:
            sampled = random.sample(bank, 5)
        else:
            sampled = list(bank)

        # Ensure question dicts have an id field for consistency
        formatted = []
        for idx, item in enumerate(sampled):
            formatted.append({
                "id": item.get("id", idx + 1),
                "question": item["question"],
                "options": item["options"],
                "answer": item["answer"]
            })
        return formatted

    def create_quiz_screen(self):
        self.root.title(self.subject + " Quiz")
        self.root.geometry("750x520")
        self.root.resizable(False, False)

        # Pastel peach background
        self.root.configure(bg="#FFF1E6")

        # Heading
        mode_suffix = " (Offline)" if self.offline_mode else ""
        self.heading = tk.Label(
            self.root,
            text=self.subject + " QUIZ" + mode_suffix,
            font=("Arial", 24, "bold"),
            bg="#FFF1E6",
            fg="#5D4057"
        )
        self.heading.pack(pady=20)

        # Question number
        self.number_label = tk.Label(
            self.root,
            text="",
            font=("Arial", 12, "bold"),
            bg="#FFF1E6",
            fg="#6D597A"
        )
        self.number_label.pack()

        # Question text
        self.question_label = tk.Label(
            self.root,
            text="",
            font=("Arial", 15),
            wraplength=650,
            bg="#FFF1E6",
            fg="#403D39"
        )
        self.question_label.pack(pady=20)

        # Four answer options
        self.option_buttons = []
        for i in range(4):
            button = tk.Radiobutton(
                self.root,
                text="",
                variable=self.selected_answer,
                value="",
                font=("Arial", 12),
                width=50,
                anchor="w",
                bg="#FFF1E6",
                fg="#403D39",
                activebackground="#FFE5D9",
                selectcolor="#FFD6BA"
            )
            button.pack(pady=4)
            self.option_buttons.append(button)

        # Next / Submit button container
        button_frame = tk.Frame(self.root, bg="#FFF1E6")
        button_frame.pack(pady=20)

        self.next_button = tk.Button(
            button_frame,
            text="Next",
            command=self.next_question,
            font=("Arial", 12, "bold"),
            width=15,
            bg="#CDB4DB",
            fg="#3E3047",
            activebackground="#B99AC8",
            relief="flat",
            cursor="hand2"
        )
        self.next_button.pack(side="left", padx=10)

    def show_question(self):
        total_q = len(self.questions)
        if total_q == 0:
            messagebox.showerror("Error", f"No questions available for {self.subject}.")
            self.return_to_home()
            return

        current_question = self.questions[self.question_number]

        # Question number
        self.number_label.config(
            text=f"Question {self.question_number + 1} of {total_q}"
        )

        # Question
        self.question_label.config(
            text=current_question["question"]
        )

        # Remove previous selection
        self.selected_answer.set("")

        # Display options
        for i in range(4):
            if i < len(current_question["options"]):
                option = current_question["options"][i]
                self.option_buttons[i].config(
                    text=option,
                    value=option,
                    state="normal"
                )
            else:
                self.option_buttons[i].config(text="", value="", state="disabled")

        # Change button text on last question
        if self.question_number == total_q - 1:
            self.next_button.config(
                text="Submit",
                bg="#FFCAD4"
            )
        else:
            self.next_button.config(
                text="Next",
                bg="#CDB4DB"
            )

    def next_question(self):
        user_answer = self.selected_answer.get()

        # Check whether an option is selected
        if user_answer == "":
            messagebox.showwarning(
                "Answer Required",
                "Please select an option before continuing."
            )
            return

        current_q = self.questions[self.question_number]
        correct_answer = current_q.get("answer", "")
        q_id = current_q.get("id", None)

        is_correct = False
        # If online and q_id exists, verify through PL/SQL function FN_CHECK_ANSWER
        if not self.offline_mode and q_id is not None:
            try:
                is_correct = database.check_answer(q_id, user_answer)
            except Exception as ex:
                print(f"[quiz_app] DB check_answer fallback: {ex}")
                is_correct = (user_answer.strip() == correct_answer.strip())
        else:
            is_correct = (user_answer.strip() == correct_answer.strip())

        if is_correct:
            self.score += 1

        # Track response
        self.responses.append({
            "question_id": q_id,
            "selected_option": user_answer,
            "correct_option": correct_answer,
            "is_correct": 1 if is_correct else 0
        })

        total_q = len(self.questions)
        # Move to next question or submit
        if self.question_number < total_q - 1:
            self.question_number += 1
            self.show_question()
        else:
            self.show_result()

    def show_result(self):
        total_questions = len(self.questions)
        percentage = (self.score / total_questions) * 100 if total_questions > 0 else 0
        result_message = ""
        attempt_id = None

        # Save to Oracle PL/SQL if not in offline mode
        if not self.offline_mode:
            try:
                db_result = database.save_full_quiz_result(
                    username=self.username,
                    subject_name=self.subject,
                    score=self.score,
                    total_questions=total_questions,
                    responses=self.responses
                )
                attempt_id = db_result["attempt_id"]
                percentage = db_result["percentage"]
                result_message = db_result["performance_message"]
            except Exception as ex:
                print(f"[quiz_app] Error saving quiz to Oracle: {ex}")
                messagebox.showerror(
                    "Database Error",
                    f"Quiz completed, but failed to persist to Oracle:\n{ex}\n\nDisplaying local result."
                )

        # Fallback local calculation if database did not provide message
        if not result_message:
            if percentage >= 80:
                result_message = "Excellent Performance!"
            elif percentage >= 60:
                result_message = "Good Performance!"
            elif percentage >= 40:
                result_message = "Average Performance!"
            else:
                result_message = "Keep Practicing!"

        # Show result summary
        stored_note = f"\nAttempt ID: #{attempt_id} (Saved to Oracle)" if attempt_id else ""
        messagebox.showinfo(
            "Quiz Result",
            f"Subject: {self.subject}\n"
            f"User: {self.username}\n\n"
            f"Score: {self.score} / {total_questions}\n"
            f"Percentage: {percentage:.0f}%\n\n"
            f"{result_message}"
            f"{stored_note}"
        )

        self.return_to_home()

    def return_to_home(self):
        """Closes current quiz window and reopens portal if callback provided."""
        self.root.destroy()
        if self.on_return_home:
            self.on_return_home()


def open_history_window(parent_root: tk.Tk, username: Optional[str] = None):
    """
    Displays past quiz attempts retrieved from Oracle PL/SQL SP_GET_USER_HISTORY
    and aggregate stats from SP_GET_SUBJECT_PERFORMANCE.
    Allows filtering by student name to easily differentiate attempts.
    """
    history_win = tk.Toplevel(parent_root)
    history_win.title("Quiz History & Statistics")
    history_win.geometry("760x530")
    history_win.configure(bg="#F3EEF9")

    # Header
    header = tk.Label(
        history_win,
        text="Previous Quiz Attempts & Leaderboard",
        font=("Arial", 18, "bold"),
        bg="#F3EEF9",
        fg="#4A4063"
    )
    header.pack(pady=10)

    # Performance summary cards frame
    stats_frame = tk.Frame(history_win, bg="#F3EEF9")
    stats_frame.pack(fill="x", padx=20, pady=4)

    try:
        stats = database.get_subject_performance()
        if stats:
            for item in stats:
                card = tk.Label(
                    stats_frame,
                    text=f"{item['subject_name']}: {item['total_attempts']} attempts | High: {item['highest_score']} | Avg: {item['avg_percentage']:.0f}%",
                    font=("Arial", 10, "bold"),
                    bg="#E2D9F3",
                    fg="#382E4B",
                    padx=10,
                    pady=4,
                    relief="ridge"
                )
                card.pack(side="left", padx=5)
    except Exception as ex:
        print(f"[history] Could not load stats: {ex}")

    # Search / Filter Bar
    filter_frame = tk.Frame(history_win, bg="#F3EEF9")
    filter_frame.pack(fill="x", padx=20, pady=8)

    tk.Label(
        filter_frame,
        text="Filter by Student Name:",
        font=("Arial", 10, "bold"),
        bg="#F3EEF9",
        fg="#4A4063"
    ).pack(side="left", padx=(0, 6))

    search_var = tk.StringVar(value=username if username else "")
    search_entry = tk.Entry(filter_frame, textvariable=search_var, font=("Arial", 10), width=18)
    search_entry.pack(side="left", padx=4)

    # Treeview for history rows
    table_frame = tk.Frame(history_win, bg="#F3EEF9")
    table_frame.pack(fill="both", expand=True, padx=20, pady=5)

    columns = ("id", "user", "subject", "score", "pct", "rating", "date")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)

    tree.heading("id", text="ID")
    tree.heading("user", text="Student Name")
    tree.heading("subject", text="Subject")
    tree.heading("score", text="Score")
    tree.heading("pct", text="%")
    tree.heading("rating", text="Rating")
    tree.heading("date", text="Date & Time")

    tree.column("id", width=45, anchor="center")
    tree.column("user", width=125, anchor="center")
    tree.column("subject", width=85, anchor="center")
    tree.column("score", width=65, anchor="center")
    tree.column("pct", width=55, anchor="center")
    tree.column("rating", width=160, anchor="w")
    tree.column("date", width=155, anchor="center")

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)

    def load_rows(user_filter: Optional[str] = None):
        for item in tree.get_children():
            tree.delete(item)
        try:
            filter_arg = user_filter.strip() if user_filter and user_filter.strip() else None
            rows = database.get_quiz_history(username=filter_arg, limit=100)
            if not rows:
                tree.insert("", "end", values=("-", "-", "No attempts found", "-", "-", "-", "-"))
            else:
                for r in rows:
                    tree.insert("", "end", values=(
                        r["attempt_id"],
                        r["username"],
                        r["subject_name"],
                        f"{r['score']}/{r['total_questions']}",
                        f"{r['percentage']:.0f}%",
                        r["performance_message"],
                        r["attempt_time"]
                    ))
        except Exception as ex:
            messagebox.showerror("Error", f"Failed to retrieve history from Oracle:\n{ex}")

    def on_filter():
        load_rows(search_var.get())

    def on_clear():
        search_var.set("")
        load_rows(None)

    filter_btn = tk.Button(
        filter_frame,
        text="Filter",
        command=on_filter,
        font=("Arial", 9, "bold"),
        width=8,
        bg="#BDE0FE",
        fg="#263238",
        relief="flat",
        cursor="hand2"
    )
    filter_btn.pack(side="left", padx=4)

    clear_btn = tk.Button(
        filter_frame,
        text="Show All",
        command=on_clear,
        font=("Arial", 9),
        width=9,
        bg="#CDEAC0",
        fg="#263238",
        relief="flat",
        cursor="hand2"
    )
    clear_btn.pack(side="left", padx=4)

    search_entry.bind("<Return>", lambda e: on_filter())

    # Initial load
    load_rows(username)

    # Close button
    close_btn = tk.Button(
        history_win,
        text="Close",
        command=history_win.destroy,
        font=("Arial", 11),
        width=12,
        bg="#FFCAD4",
        fg="#4A3038",
        relief="flat",
        cursor="hand2"
    )
    close_btn.pack(pady=10)