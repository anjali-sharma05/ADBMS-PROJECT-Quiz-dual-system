"""
main.py - Application entry point for the MCA Dual Quiz Portal.
Connects Tkinter UI to Oracle PL/SQL database for dynamic subject loading,
user identification, quiz execution, and history inspection.
"""

import tkinter as tk
from tkinter import messagebox
from typing import List, Dict, Any, Optional

from quiz_app import QuizApp, open_history_window
import database


def start_quiz_with_user(subject_name: str, username: str, root_window: tk.Tk):
    """Destroys portal window and launches the QuizApp for the chosen subject and user."""
    root_window.destroy()

    quiz_window = tk.Tk()
    QuizApp(
        root=quiz_window,
        subject=subject_name,
        question_bank=None,
        username=username,
        on_return_home=create_main_portal
    )
    quiz_window.mainloop()


def ask_student_name_and_start(subject_name: str, root_window: tk.Tk):
    """
    Displays a modal dialog asking the student for their name before starting the quiz.
    Ensures attempt records in Oracle have distinct user names.
    """
    dialog = tk.Toplevel(root_window)
    dialog.title(f"Enter Name - {subject_name} Quiz")
    dialog.geometry("440x260")
    dialog.resizable(False, False)
    dialog.configure(bg="#EDE7F6")
    dialog.transient(root_window)
    dialog.grab_set()

    # Center dialog on parent window
    root_x = root_window.winfo_x()
    root_y = root_window.winfo_y()
    root_w = root_window.winfo_width()
    root_h = root_window.winfo_height()
    dialog_x = root_x + (root_w // 2) - 220
    dialog_y = root_y + (root_h // 2) - 130
    dialog.geometry(f"440x260+{max(0, dialog_x)}+{max(0, dialog_y)}")

    # Dialog Title
    title = tk.Label(
        dialog,
        text=f"{subject_name} Quiz Registration",
        font=("Arial", 16, "bold"),
        bg="#EDE7F6",
        fg="#4A4063"
    )
    title.pack(pady=(22, 6))

    prompt_label = tk.Label(
        dialog,
        text="Please enter your name to begin:",
        font=("Arial", 12),
        bg="#EDE7F6",
        fg="#5F5874"
    )
    prompt_label.pack(pady=4)

    # Name Entry Field
    name_var = tk.StringVar()
    entry = tk.Entry(
        dialog,
        textvariable=name_var,
        font=("Arial", 13),
        width=25,
        justify="center",
        bd=2,
        relief="groove"
    )
    entry.pack(pady=14)
    entry.focus_set()

    def confirm_and_start(event=None):
        name = name_var.get().strip()
        if not name:
            messagebox.showwarning(
                "Name Required",
                "Please enter your name before continuing to the quiz.",
                parent=dialog
            )
            entry.focus_set()
            return

        dialog.destroy()
        start_quiz_with_user(subject_name, name, root_window)

    # Allow pressing 'Enter' key to start
    entry.bind("<Return>", confirm_and_start)

    # Button Row
    btn_frame = tk.Frame(dialog, bg="#EDE7F6")
    btn_frame.pack(pady=10)

    start_btn = tk.Button(
        btn_frame,
        text="Start Quiz",
        command=confirm_and_start,
        font=("Arial", 11, "bold"),
        width=13,
        height=1,
        bg="#BDE0FE",
        fg="#263238",
        activebackground="#A9D6F5",
        relief="flat",
        cursor="hand2"
    )
    start_btn.pack(side="left", padx=8)

    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        command=dialog.destroy,
        font=("Arial", 11),
        width=10,
        height=1,
        bg="#FFCAD4",
        fg="#4A3038",
        activebackground="#F5B7C3",
        relief="flat",
        cursor="hand2"
    )
    cancel_btn.pack(side="left", padx=8)


def test_db_status():
    """Tests the Oracle connection and reports status to user."""
    success, message = database.test_connection()
    if success:
        messagebox.showinfo("Oracle Database Status", f"Connection SUCCESSFUL!\n\n{message}")
    else:
        messagebox.showwarning(
            "Oracle Connection Notice",
            f"Could not connect to Oracle Database:\n\n{message}\n\n"
            "The app will continue in offline mode using local question banks.\n"
            "Please check your .env settings and ensure the Oracle service is running."
        )


def load_portal_subjects() -> List[str]:
    """
    Attempts to fetch available subjects from Oracle PL/SQL.
    Falls back to ['Python', 'DAA'] if database is unavailable.
    """
    try:
        db_subjects = database.get_subjects()
        if db_subjects:
            return [s["subject_name"] for s in db_subjects]
    except Exception as ex:
        print(f"[main.py] Could not fetch subjects from Oracle ({ex}). Using defaults.")
    return ["Python", "DAA"]


def create_main_portal():
    """Builds and displays the main MCA Quiz Portal Tkinter window."""
    root = tk.Tk()
    root.title("MCA Quiz Portal")
    root.geometry("700x530")
    root.resizable(False, False)
    root.configure(bg="#EDE7F6")

    # Title
    title = tk.Label(
        root,
        text="MCA QUIZ PORTAL",
        font=("Arial", 26, "bold"),
        bg="#EDE7F6",
        fg="#4A4063"
    )
    title.pack(pady=(35, 10))

    # Subtitle
    subtitle = tk.Label(
        root,
        text="Choose a subject to begin your quiz",
        font=("Arial", 14),
        bg="#EDE7F6",
        fg="#5F5874"
    )
    subtitle.pack(pady=5)

    # Subject Buttons Container
    subjects_frame = tk.Frame(root, bg="#EDE7F6")
    subjects_frame.pack(pady=15)

    subjects = load_portal_subjects()

    # Palette for subject buttons
    palette = [
        {"bg": "#BDE0FE", "fg": "#263238", "abg": "#A9D6F5"},  # Python soft blue
        {"bg": "#CDEAC0", "fg": "#263238", "abg": "#B8DDAA"},  # DAA soft green
        {"bg": "#E8DFF5", "fg": "#263238", "abg": "#D6C6EE"},  # Soft lavender
        {"bg": "#FCE1E4", "fg": "#263238", "abg": "#F9CAD0"},  # Soft coral
    ]

    for idx, subj in enumerate(subjects):
        color = palette[idx % len(palette)]
        btn = tk.Button(
            subjects_frame,
            text=f"{subj} Quiz",
            command=lambda s=subj: ask_student_name_and_start(s, root),
            font=("Arial", 14, "bold"),
            width=22,
            height=2,
            bg=color["bg"],
            fg=color["fg"],
            activebackground=color["abg"],
            relief="flat",
            cursor="hand2"
        )
        btn.pack(pady=6)

    # Secondary Action Buttons Frame (History, DB Status, Exit)
    action_frame = tk.Frame(root, bg="#EDE7F6")
    action_frame.pack(pady=15)

    history_button = tk.Button(
        action_frame,
        text="View Quiz History",
        command=lambda: open_history_window(root, username=None),
        font=("Arial", 11, "bold"),
        width=16,
        bg="#D8B4E2",
        fg="#352641",
        activebackground="#C79DCE",
        relief="flat",
        cursor="hand2"
    )
    history_button.pack(side="left", padx=8)

    test_button = tk.Button(
        action_frame,
        text="Test DB Status",
        command=test_db_status,
        font=("Arial", 11),
        width=14,
        bg="#C2DFE3",
        fg="#2B4141",
        activebackground="#ADCED3",
        relief="flat",
        cursor="hand2"
    )
    test_button.pack(side="left", padx=8)

    exit_button = tk.Button(
        action_frame,
        text="Exit",
        command=root.destroy,
        font=("Arial", 11),
        width=10,
        bg="#FFCAD4",
        fg="#4A3038",
        activebackground="#F5B7C3",
        relief="flat",
        cursor="hand2"
    )
    exit_button.pack(side="left", padx=8)

    root.mainloop()


if __name__ == "__main__":
    create_main_portal()