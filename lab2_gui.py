import io
import tkinter as tk
from contextlib import redirect_stdout
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from lab2 import (
    ElectionCommission,
    Voter,
    issue_signed_set,
    make_ballot,
    parse_ballot,
)


class VotingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Е-голосування зі сліпими підписами")
        self.root.geometry("1180x760")
        self.root.minsize(1000, 680)

        self.candidates = ["Кандидат 1", "Кандидат 2"]
        self.voter_names = [
            "Іваненко Іван Іванович",
            "Петренко Петро Петрович",
            "Сидоренко Анна Олегівна",
            "Коваль Марія Сергіївна",
            "Бондаренко Олег Андрійович",
        ]

        self.build_ui()
        self.reset_system(show_message=False)

    def build_ui(self):
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(18, 14))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="Протокол Е-голосування зі сліпими підписами",
            font=("Segoe UI", 17, "bold"),
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            header,
            text="RSA · 5 виборців · 2 кандидати · 10 наборів бюлетенів",
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        ttk.Button(
            header,
            text="Скинути систему",
            command=self.reset_system,
        ).grid(row=0, column=1, rowspan=2, padx=(16, 0), sticky="e")

        content = ttk.Panedwindow(self.root, orient="horizontal")
        content.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

        left = ttk.Frame(content, padding=12)
        right = ttk.Frame(content, padding=12)
        content.add(left, weight=1)
        content.add(right, weight=2)

        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)

        vote_box = ttk.LabelFrame(left, text="Голосування", padding=12)
        vote_box.grid(row=0, column=0, sticky="ew")
        vote_box.columnconfigure(1, weight=1)

        ttk.Label(vote_box, text="Виборець:").grid(row=0, column=0, sticky="w", pady=5)

        self.voter_var = tk.StringVar()
        self.voter_combo = ttk.Combobox(
            vote_box,
            textvariable=self.voter_var,
            values=self.voter_names,
            state="readonly",
        )
        self.voter_combo.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=5)
        self.voter_combo.current(0)

        ttk.Label(vote_box, text="Кандидат:").grid(row=1, column=0, sticky="w", pady=5)

        self.candidate_var = tk.StringVar()
        self.candidate_combo = ttk.Combobox(
            vote_box,
            textvariable=self.candidate_var,
            values=self.candidates,
            state="readonly",
        )
        self.candidate_combo.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=5)
        self.candidate_combo.current(0)

        ttk.Button(
            vote_box,
            text="1. Отримати підписаний набір",
            command=self.action_issue_set,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 5))

        ttk.Button(
            vote_box,
            text="2. Проголосувати",
            command=self.action_vote,
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)

        tests_box = ttk.LabelFrame(left, text="Тестування", padding=12)
        tests_box.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        tests_box.columnconfigure(0, weight=1)

        ttk.Button(
            tests_box,
            text="Повторне отримання набору",
            command=self.test_repeat_set,
        ).grid(row=0, column=0, sticky="ew", pady=4)

        ttk.Button(
            tests_box,
            text="Два бюлетені з одного набору",
            command=self.test_double_vote,
        ).grid(row=1, column=0, sticky="ew", pady=4)

        ttk.Button(
            tests_box,
            text="Некоректний розкритий набір",
            command=self.test_bad_opened_set,
        ).grid(row=2, column=0, sticky="ew", pady=4)

        ttk.Button(
            tests_box,
            text="Неправильний підпис",
            command=self.test_bad_signature,
        ).grid(row=3, column=0, sticky="ew", pady=4)

        state_box = ttk.LabelFrame(left, text="Стан виборців", padding=10)
        state_box.grid(row=2, column=0, sticky="nsew", pady=(14, 0))

        self.state_tree = ttk.Treeview(
            state_box,
            columns=("name", "signed", "voted"),
            show="headings",
            height=7,
        )
        self.state_tree.heading("name", text="Виборець")
        self.state_tree.heading("signed", text="Набір")
        self.state_tree.heading("voted", text="Голос")
        self.state_tree.column("name", width=210, anchor="w")
        self.state_tree.column("signed", width=90, anchor="center")
        self.state_tree.column("voted", width=90, anchor="center")
        self.state_tree.pack(fill="both", expand=True)

        notebook = ttk.Notebook(right)
        notebook.pack(fill="both", expand=True)

        log_tab = ttk.Frame(notebook, padding=10)
        results_tab = ttk.Frame(notebook, padding=10)
        notebook.add(log_tab, text="Журнал")
        notebook.add(results_tab, text="Результати")

        self.log_text = ScrolledText(
            log_tab,
            wrap="word",
            font=("Consolas", 10),
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True)

        results_tab.columnconfigure(0, weight=1)
        results_tab.rowconfigure(2, weight=1)

        ttk.Label(
            results_tab,
            text="Поточний підрахунок",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.results_tree = ttk.Treeview(
            results_tab,
            columns=("candidate", "votes"),
            show="headings",
            height=4,
        )
        self.results_tree.heading("candidate", text="Кандидат")
        self.results_tree.heading("votes", text="Голоси")
        self.results_tree.column("candidate", width=220, anchor="w")
        self.results_tree.column("votes", width=100, anchor="center")
        self.results_tree.grid(row=1, column=0, sticky="ew")

        ttk.Label(
            results_tab,
            text="Прийняті анонімні бюлетені",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=2, column=0, sticky="sw", pady=(15, 6))

        self.ballots_tree = ttk.Treeview(
            results_tab,
            columns=("id", "candidate", "signature"),
            show="headings",
        )
        self.ballots_tree.heading("id", text="ID")
        self.ballots_tree.heading("candidate", text="Кандидат")
        self.ballots_tree.heading("signature", text="Підпис ВК")
        self.ballots_tree.column("id", width=180, anchor="w")
        self.ballots_tree.column("candidate", width=140, anchor="w")
        self.ballots_tree.column("signature", width=180, anchor="w")
        self.ballots_tree.grid(row=3, column=0, sticky="nsew")

        ttk.Button(
            results_tab,
            text="Оновити результати",
            command=self.refresh_results,
        ).grid(row=4, column=0, sticky="ew", pady=(10, 0))

    def append_log(self, text):
        if not text:
            return
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def section(self, title):
        self.append_log("\n" + title)

    def run_and_capture(self, func, *args, **kwargs):
        buffer = io.StringIO()
        try:
            with redirect_stdout(buffer):
                result = func(*args, **kwargs)
        except Exception as error:
            result = None
            self.append_log(buffer.getvalue())
            self.append_log(f"Помилка: {error}")
            return result

        self.append_log(buffer.getvalue())
        return result

    def reset_system(self, show_message=True):
        self.voters = {name: Voter(name) for name in self.voter_names}
        self.commission = ElectionCommission(self.candidates, self.voter_names)

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        self.append_log("Систему ініціалізовано.")
        self.append_log(f"Відкритий ключ ВК: {self.commission.public_key}")
        self.refresh_state()
        self.refresh_results()

        if show_message:
            messagebox.showinfo("Готово", "Систему скинуто до початкового стану.")

    def selected_voter(self):
        return self.voters[self.voter_var.get()]

    def refresh_state(self):
        for item in self.state_tree.get_children():
            self.state_tree.delete(item)

        for name in self.voter_names:
            voter = self.voters[name]
            signed = "так" if name in self.commission.issued_voters else "ні"
            voted = "ні"

            if voter.signed_set_index is not None:
                ballot_id = voter.ballot_sets[voter.signed_set_index]["id"]
                if ballot_id in self.commission.used_ids:
                    voted = "так"

            self.state_tree.insert("", "end", values=(name, signed, voted))

    def refresh_results(self):
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        for item in self.ballots_tree.get_children():
            self.ballots_tree.delete(item)

        results = {candidate: 0 for candidate in self.candidates}
        for ballot in self.commission.accepted_ballots:
            results[ballot["candidate"]] += 1

        for candidate, votes in results.items():
            self.results_tree.insert("", "end", values=(candidate, votes))

        for ballot in self.commission.accepted_ballots:
            self.ballots_tree.insert(
                "",
                "end",
                values=(ballot["id"], ballot["candidate"], ballot["signature"]),
            )

    def action_issue_set(self):
        voter = self.selected_voter()
        self.section(f"Отримання підписаного набору: {voter.full_name}")
        self.run_and_capture(issue_signed_set, voter, self.commission)
        self.refresh_state()

    def action_vote(self):
        voter = self.selected_voter()
        candidate = self.candidate_var.get()
        self.section(f"Голосування: {voter.full_name} → {candidate}")

        try:
            encrypted_vote = voter.create_vote(candidate, self.commission.public_key)
        except Exception as error:
            self.append_log(f"Помилка: {error}")
            return

        self.run_and_capture(self.commission.receive_vote, encrypted_vote)
        self.refresh_state()
        self.refresh_results()

    def test_repeat_set(self):
        voter = self.selected_voter()
        self.section(f"Тест: повторне отримання набору ({voter.full_name})")

        if voter.full_name not in self.commission.issued_voters:
            self.append_log("Спочатку виборець отримає один коректний підписаний набір.")
            success = self.run_and_capture(issue_signed_set, voter, self.commission)
            if not success:
                self.refresh_state()
                return

        masked_sets = voter.prepare_ballot_sets(self.candidates, self.commission.public_key)
        self.run_and_capture(
            self.commission.choose_sets_for_check,
            voter.full_name,
            masked_sets,
        )
        self.refresh_state()

    def test_double_vote(self):
        voter = self.selected_voter()
        first_candidate = self.candidate_var.get()
        second_candidate = next(c for c in self.candidates if c != first_candidate)
        self.section(f"Тест: два бюлетені з одного набору ({voter.full_name})")

        if voter.full_name not in self.commission.issued_voters:
            success = self.run_and_capture(issue_signed_set, voter, self.commission)
            if not success:
                self.refresh_state()
                return

        ballot_id = voter.ballot_sets[voter.signed_set_index]["id"]

        if ballot_id not in self.commission.used_ids:
            self.append_log(f"Перший бюлетень: {first_candidate}")
            first_vote = voter.create_vote(first_candidate, self.commission.public_key)
            self.run_and_capture(self.commission.receive_vote, first_vote)

        self.append_log(f"Другий бюлетень з тим самим ID: {second_candidate}")
        second_vote = voter.create_vote(second_candidate, self.commission.public_key)
        self.run_and_capture(self.commission.receive_vote, second_vote)

        self.refresh_state()
        self.refresh_results()

    def test_bad_opened_set(self):
        self.section("Тест: некоректний розкритий набір")

        voter = next(
            (
                self.voters[name]
                for name in self.voter_names
                if name not in self.commission.issued_voters
            ),
            None,
        )

        if voter is None:
            self.append_log("Немає виборця без підписаного набору. Скиньте систему для повторного тесту.")
            return

        self.append_log(f"Для тесту використовується: {voter.full_name}")

        masked_sets = voter.prepare_ballot_sets(self.candidates, self.commission.public_key)
        selection = self.run_and_capture(
            self.commission.choose_sets_for_check,
            voter.full_name,
            masked_sets,
        )

        if selection is None:
            return

        opened_indices, hidden_index = selection
        revealed_sets = voter.reveal_sets(opened_indices)
        bad_index = opened_indices[0]
        ballot_id, _ = parse_ballot(revealed_sets[bad_index][0]["ballot"])
        revealed_sets[bad_index][0]["ballot"] = make_ballot(ballot_id, self.candidates[1])

        self.append_log(f"Набір {bad_index + 1} навмисно змінено.")

        self.run_and_capture(
            self.commission.verify_opened_sets_and_sign,
            voter.full_name,
            masked_sets,
            opened_indices,
            hidden_index,
            revealed_sets,
        )
        self.refresh_state()

    def test_bad_signature(self):
        voter = self.selected_voter()
        self.section(f"Тест: неправильний підпис ({voter.full_name})")

        if voter.full_name not in self.commission.issued_voters:
            success = self.run_and_capture(issue_signed_set, voter, self.commission)
            if not success:
                self.refresh_state()
                return

        tampered_vote = voter.create_tampered_vote(
            self.candidates[0],
            self.candidates[1],
            self.commission.public_key,
        )
        self.run_and_capture(self.commission.receive_vote, tampered_vote)
        self.refresh_state()
        self.refresh_results()


def main():
    root = tk.Tk()
    VotingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
