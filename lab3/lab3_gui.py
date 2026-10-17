import io
import contextlib
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from lab3 import Voter
from registration_bureau import RegistrationBureau
from election_commission import ElectionCommission


class VotingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторна робота №3 — Розподіл повноважень")
        self.root.geometry("1220x780")
        self.root.minsize(1060, 680)

        self.candidates = [
            "Кандидат 1",
            "Кандидат 2"
        ]

        self.voter_names = [
            "Іваненко Іван Іванович",
            "Петренко Петро Петрович",
            "Сидоренко Анна Олегівна",
            "Коваль Марія Сергіївна",
            "Бондаренко Олег Андрійович"
        ]

        self.create_system()
        self.create_widgets()
        self.refresh_state()
        self.refresh_results()

        self.append_log("Систему ініціалізовано.")
        self.append_log(f"Відкритий ключ ВК: {self.commission.public_key}")

    def create_system(self):
        self.voters = [
            Voter(name)
            for name in self.voter_names
        ]

        self.bureau = RegistrationBureau(
            self.voter_names
        )

        self.commission = ElectionCommission(
            self.candidates
        )

    def create_widgets(self):
        style = ttk.Style()

        try:
            style.theme_use("vista")
        except tk.TclError:
            pass

        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 17, "bold")
        )

        style.configure(
            "Section.TLabelframe.Label",
            font=("Segoe UI", 10, "bold")
        )

        main = ttk.Frame(
            self.root,
            padding=14
        )
        main.pack(
            fill="both",
            expand=True
        )

        title = ttk.Label(
            main,
            text="Протокол Е-голосування з розподілом повноважень",
            style="Title.TLabel"
        )
        title.pack(
            anchor="w",
            pady=(0, 12)
        )

        body = ttk.Frame(main)
        body.pack(
            fill="both",
            expand=True
        )

        left = ttk.Frame(
            body,
            width=330
        )
        left.pack(
            side="left",
            fill="y",
            padx=(0, 12)
        )
        left.pack_propagate(False)

        right = ttk.Frame(body)
        right.pack(
            side="left",
            fill="both",
            expand=True
        )

        selection = ttk.LabelFrame(
            left,
            text="Вибір",
            padding=10,
            style="Section.TLabelframe"
        )
        selection.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Label(
            selection,
            text="Виборець:"
        ).pack(
            anchor="w"
        )

        self.voter_var = tk.StringVar(
            value=self.voter_names[0]
        )

        self.voter_combo = ttk.Combobox(
            selection,
            textvariable=self.voter_var,
            values=self.voter_names,
            state="readonly"
        )
        self.voter_combo.pack(
            fill="x",
            pady=(3, 9)
        )
        self.voter_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.refresh_state()
        )

        ttk.Label(
            selection,
            text="Кандидат:"
        ).pack(
            anchor="w"
        )

        self.candidate_var = tk.StringVar(
            value=self.candidates[0]
        )

        ttk.Combobox(
            selection,
            textvariable=self.candidate_var,
            values=self.candidates,
            state="readonly"
        ).pack(
            fill="x",
            pady=(3, 0)
        )

        actions = ttk.LabelFrame(
            left,
            text="Основні дії",
            padding=10,
            style="Section.TLabelframe"
        )
        actions.pack(
            fill="x",
            pady=(0, 10)
        )

        self.make_button(
            actions,
            "Зареєструвати виборця",
            self.register_selected
        )

        self.make_button(
            actions,
            "Передати дані БР → ВК",
            self.transfer_registration_data
        )

        self.make_button(
            actions,
            "Проголосувати",
            self.vote
        )

        self.make_button(
            actions,
            "Перевірити свій голос",
            self.verify_own_vote
        )

        tests = ttk.LabelFrame(
            left,
            text="Перевірки",
            padding=10,
            style="Section.TLabelframe"
        )
        tests.pack(
            fill="x",
            pady=(0, 10)
        )

        self.make_button(
            tests,
            "Повторне отримання RN",
            self.test_repeat_rn
        )

        self.make_button(
            tests,
            "Невалідний RN",
            self.test_invalid_rn
        )

        self.make_button(
            tests,
            "Вже використаний RN",
            self.test_used_rn
        )

        self.make_button(
            tests,
            "Повторний ID",
            self.test_duplicate_id
        )

        self.make_button(
            tests,
            "Неправильний ЕЦП",
            self.test_wrong_signature
        )

        self.make_button(
            tests,
            "Невідповідність публікації",
            self.test_publication_mismatch
        )

        system = ttk.LabelFrame(
            left,
            text="Система",
            padding=10,
            style="Section.TLabelframe"
        )
        system.pack(
            fill="x"
        )

        self.make_button(
            system,
            "Зареєструвати всіх",
            self.register_all
        )

        self.make_button(
            system,
            "Скинути систему",
            self.reset_system
        )

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(
            fill="both",
            expand=True
        )

        self.log_tab = ttk.Frame(
            self.notebook,
            padding=8
        )
        self.state_tab = ttk.Frame(
            self.notebook,
            padding=8
        )
        self.results_tab = ttk.Frame(
            self.notebook,
            padding=8
        )

        self.notebook.add(
            self.log_tab,
            text="Журнал"
        )
        self.notebook.add(
            self.state_tab,
            text="Стан БР і ВК"
        )
        self.notebook.add(
            self.results_tab,
            text="Результати"
        )

        self.log_text = ScrolledText(
            self.log_tab,
            wrap="word",
            font=("Consolas", 10),
            state="disabled"
        )
        self.log_text.pack(
            fill="both",
            expand=True
        )

        self.create_state_tab()
        self.create_results_tab()

    def make_button(self, parent, text, command):
        ttk.Button(
            parent,
            text=text,
            command=command
        ).pack(
            fill="x",
            pady=3
        )

    def create_state_tab(self):
        key_frame = ttk.Frame(
            self.state_tab
        )
        key_frame.pack(
            fill="x",
            pady=(0, 8)
        )

        self.key_label = ttk.Label(
            key_frame,
            text=""
        )
        self.key_label.pack(
            anchor="w"
        )

        bureau_frame = ttk.LabelFrame(
            self.state_tab,
            text="Бюро реєстрації — знає особу виборця",
            padding=8
        )
        bureau_frame.pack(
            fill="both",
            expand=True,
            pady=(0, 8)
        )

        self.bureau_tree = ttk.Treeview(
            bureau_frame,
            columns=("voter", "rn", "key"),
            show="headings",
            height=6
        )

        self.bureau_tree.heading(
            "voter",
            text="Виборець"
        )
        self.bureau_tree.heading(
            "rn",
            text="RN"
        )
        self.bureau_tree.heading(
            "key",
            text="Відкритий ключ виборця"
        )

        self.bureau_tree.column(
            "voter",
            width=240
        )
        self.bureau_tree.column(
            "rn",
            width=130,
            anchor="center"
        )
        self.bureau_tree.column(
            "key",
            width=250
        )

        self.bureau_tree.pack(
            fill="both",
            expand=True
        )

        commission_frame = ttk.LabelFrame(
            self.state_tab,
            text="Виборча комісія — отримує RN без персональних даних",
            padding=8
        )
        commission_frame.pack(
            fill="both",
            expand=True
        )

        self.commission_tree = ttk.Treeview(
            commission_frame,
            columns=("rn", "key", "status"),
            show="headings",
            height=6
        )

        self.commission_tree.heading(
            "rn",
            text="RN"
        )
        self.commission_tree.heading(
            "key",
            text="Відкритий ключ виборця"
        )
        self.commission_tree.heading(
            "status",
            text="Статус RN"
        )

        self.commission_tree.column(
            "rn",
            width=150,
            anchor="center"
        )
        self.commission_tree.column(
            "key",
            width=300
        )
        self.commission_tree.column(
            "status",
            width=150,
            anchor="center"
        )

        self.commission_tree.pack(
            fill="both",
            expand=True
        )

    def create_results_tab(self):
        self.results_summary = ttk.Label(
            self.results_tab,
            text="",
            font=("Segoe UI", 12, "bold")
        )
        self.results_summary.pack(
            anchor="w",
            pady=(0, 10)
        )

        self.results_tree = ttk.Treeview(
            self.results_tab,
            columns=("id", "candidate", "signature"),
            show="headings"
        )

        self.results_tree.heading(
            "id",
            text="ID"
        )
        self.results_tree.heading(
            "candidate",
            text="Кандидат"
        )
        self.results_tree.heading(
            "signature",
            text="ЕЦП виборця"
        )

        self.results_tree.column(
            "id",
            width=190,
            anchor="center"
        )
        self.results_tree.column(
            "candidate",
            width=180,
            anchor="center"
        )
        self.results_tree.column(
            "signature",
            width=260,
            anchor="center"
        )

        self.results_tree.pack(
            fill="both",
            expand=True
        )

    def append_log(self, text):
        if text is None:
            return

        text = str(text)

        self.log_text.configure(
            state="normal"
        )

        if text.strip() == "":
            self.log_text.insert(
                "end",
                "\n"
            )
        else:
            self.log_text.insert(
                "end",
                text.rstrip() + "\n"
            )

        self.log_text.see("end")
        self.log_text.configure(
            state="disabled"
        )

    def section(self, title):
        self.append_log("")
        self.append_log(title)

    def run_and_capture(self, function, *args, **kwargs):
        buffer = io.StringIO()

        try:
            with contextlib.redirect_stdout(buffer):
                result = function(
                    *args,
                    **kwargs
                )
        except Exception as error:
            output = buffer.getvalue()
            if output:
                self.append_log(output)

            self.append_log(
                f"Помилка: {error}"
            )
            return None

        output = buffer.getvalue()

        if output:
            self.append_log(output)

        return result

    def selected_voter(self):
        name = self.voter_var.get()

        return next(
            voter
            for voter in self.voters
            if voter.full_name == name
        )

    def register_selected(self):
        voter = self.selected_voter()

        self.section(
            f"Реєстрація: {voter.full_name}"
        )

        self.run_and_capture(
            voter.register,
            self.bureau
        )

        self.refresh_state()

    def register_all(self):
        self.section(
            "Реєстрація всіх виборців"
        )

        for voter in self.voters:
            if voter.rn is None:
                self.run_and_capture(
                    voter.register,
                    self.bureau
                )

        self.refresh_state()

    def transfer_registration_data(self):
        self.section(
            "Передача даних від БР до ВК"
        )

        data = self.bureau.export_registration_data()

        self.run_and_capture(
            self.commission.load_registration_data,
            data
        )

        self.refresh_state()

    def vote(self):
        voter = self.selected_voter()
        candidate = self.candidate_var.get()

        self.section(
            f"Голосування: {voter.full_name} → {candidate}"
        )

        if voter.rn is None:
            self.append_log(
                "Виборець ще не зареєстрований у БР."
            )
            return

        if voter.rn not in self.commission.registered_rns:
            self.append_log(
                "RN виборця ще не передано від БР до ВК."
            )
            return

        result = self.run_and_capture(
            voter.create_vote,
            candidate,
            self.commission.public_key,
            None,
            None,
            False,
            False
        )

        if result is None:
            return

        encrypted_vote, vote_id = result

        accepted = self.run_and_capture(
            self.commission.receive_vote,
            encrypted_vote
        )

        if accepted:
            voter.last_vote_id = vote_id
            voter.last_candidate = candidate

        self.refresh_state()
        self.refresh_results()

    def verify_own_vote(self):
        voter = self.selected_voter()

        self.section(
            f"Перевірка власного голосу: {voter.full_name}"
        )

        self.run_and_capture(
            voter.verify_published_vote,
            self.commission.get_published_ballots()
        )

    def ensure_registered(self, voter):
        if voter.rn is None:
            self.append_log(
                f"Для тесту спочатку реєструємо: {voter.full_name}"
            )

            self.run_and_capture(
                voter.register,
                self.bureau
            )

        if voter.rn not in self.commission.registered_rns:
            self.run_and_capture(
                self.commission.load_registration_data,
                self.bureau.export_registration_data()
            )

    def find_unused_voter(self, preferred=None, exclude=None):
        exclude = set(exclude or [])

        ordered = []

        if preferred is not None:
            ordered.append(preferred)

        ordered.extend(
            voter
            for voter in self.voters
            if voter is not preferred
        )

        for voter in ordered:
            if voter.full_name in exclude:
                continue

            if voter.rn is None:
                self.run_and_capture(
                    voter.register,
                    self.bureau
                )

            if voter.rn not in self.commission.used_rns:
                self.run_and_capture(
                    self.commission.load_registration_data,
                    self.bureau.export_registration_data()
                )
                return voter

        return None

    def test_repeat_rn(self):
        voter = self.selected_voter()

        self.section(
            f"Тест: повторне отримання RN ({voter.full_name})"
        )

        if voter.rn is None:
            self.append_log(
                "Спочатку виборець отримає один коректний RN."
            )

            self.run_and_capture(
                voter.register,
                self.bureau
            )

        self.run_and_capture(
            voter.register,
            self.bureau
        )

        self.refresh_state()

    def test_invalid_rn(self):
        voter = self.selected_voter()

        self.section(
            f"Тест: невалідний RN ({voter.full_name})"
        )

        self.ensure_registered(voter)

        fake_rn = 999999999999

        while fake_rn in self.commission.registered_rns:
            fake_rn -= 1

        result = self.run_and_capture(
            voter.create_vote,
            self.candidate_var.get(),
            self.commission.public_key,
            None,
            fake_rn,
            False,
            False
        )

        if result is not None:
            encrypted_vote, _ = result

            self.run_and_capture(
                self.commission.receive_vote,
                encrypted_vote
            )

        self.refresh_state()
        self.refresh_results()

    def test_used_rn(self):
        voter = self.selected_voter()
        candidate = self.candidate_var.get()

        self.section(
            f"Тест: повторне використання RN ({voter.full_name})"
        )

        self.ensure_registered(voter)

        if voter.rn not in self.commission.used_rns:
            self.append_log(
                "Спочатку з цим RN буде подано один коректний голос."
            )

            first = self.run_and_capture(
                voter.create_vote,
                candidate,
                self.commission.public_key,
                None,
                None,
                False,
                False
            )

            if first is None:
                return

            encrypted_vote, vote_id = first

            accepted = self.run_and_capture(
                self.commission.receive_vote,
                encrypted_vote
            )

            if not accepted:
                self.refresh_state()
                self.refresh_results()
                return

            voter.last_vote_id = vote_id
            voter.last_candidate = candidate

        second_candidate = next(
            item
            for item in self.candidates
            if item != candidate
        )

        second = self.run_and_capture(
            voter.create_vote,
            second_candidate,
            self.commission.public_key,
            None,
            None,
            False,
            False
        )

        if second is not None:
            encrypted_vote, _ = second

            self.run_and_capture(
                self.commission.receive_vote,
                encrypted_vote
            )

        self.refresh_state()
        self.refresh_results()

    def test_duplicate_id(self):
        preferred = self.selected_voter()

        self.section(
            "Тест: повторне використання ID"
        )

        if not self.commission.accepted_ballots:
            source = next(
                voter
                for voter in self.voters
                if voter is not preferred
            )

            self.append_log(
                f"Для тесту спочатку створюємо коректний голос: {source.full_name}"
            )

            self.ensure_registered(source)

            first = self.run_and_capture(
                source.create_vote,
                self.candidates[0],
                self.commission.public_key,
                None,
                None,
                False,
                False
            )

            if first is None:
                return

            encrypted_vote, vote_id = first

            accepted = self.run_and_capture(
                self.commission.receive_vote,
                encrypted_vote
            )

            if accepted:
                source.last_vote_id = vote_id
                source.last_candidate = self.candidates[0]

        if not self.commission.accepted_ballots:
            self.append_log(
                "Не вдалося створити використаний ID для тесту."
            )
            return

        used_id = self.commission.accepted_ballots[0]["id"]

        target = self.find_unused_voter(
            preferred=preferred
        )

        if target is None:
            self.append_log(
                "Немає виборця з невикористаним RN. Скиньте систему для повторення тесту."
            )
            return

        self.append_log(
            f"Повторний ID {used_id} надсилає: {target.full_name}"
        )

        result = self.run_and_capture(
            target.create_vote,
            self.candidate_var.get(),
            self.commission.public_key,
            used_id,
            None,
            False,
            False
        )

        if result is not None:
            encrypted_vote, _ = result

            self.run_and_capture(
                self.commission.receive_vote,
                encrypted_vote
            )

        self.refresh_state()
        self.refresh_results()

    def test_wrong_signature(self):
        preferred = self.selected_voter()

        self.section(
            "Тест: неправильний ЕЦП"
        )

        voter = self.find_unused_voter(
            preferred=preferred
        )

        if voter is None:
            self.append_log(
                "Немає виборця з невикористаним RN. Скиньте систему для повторення тесту."
            )
            return

        self.append_log(
            f"Тестовий виборець: {voter.full_name}"
        )

        result = self.run_and_capture(
            voter.create_vote,
            self.candidate_var.get(),
            self.commission.public_key,
            None,
            None,
            True,
            False
        )

        if result is not None:
            encrypted_vote, _ = result

            self.run_and_capture(
                self.commission.receive_vote,
                encrypted_vote
            )

        self.refresh_state()
        self.refresh_results()

    def test_publication_mismatch(self):
        preferred = self.selected_voter()

        self.section(
            "Тест: невідповідність опублікованого бюлетеня"
        )

        published = self.commission.get_published_ballots()

        voter = None

        if preferred.last_vote_id is not None:
            if any(
                item["id"] == preferred.last_vote_id
                for item in published
            ):
                voter = preferred

        if voter is None:
            for item in self.voters:
                if item.last_vote_id is not None and any(
                    ballot["id"] == item.last_vote_id
                    for ballot in published
                ):
                    voter = item
                    break

        if voter is None:
            voter = self.find_unused_voter(
                preferred=preferred
            )

            if voter is None:
                self.append_log(
                    "Немає доступного виборця для створення тестового голосу."
                )
                return

            self.append_log(
                f"Для тесту спочатку створюємо коректний голос: {voter.full_name}"
            )

            result = self.run_and_capture(
                voter.create_vote,
                self.candidates[0],
                self.commission.public_key,
                None,
                None,
                False,
                False
            )

            if result is None:
                return

            encrypted_vote, vote_id = result

            accepted = self.run_and_capture(
                self.commission.receive_vote,
                encrypted_vote
            )

            if not accepted:
                return

            voter.last_vote_id = vote_id
            voter.last_candidate = self.candidates[0]
            published = self.commission.get_published_ballots()

        fake_publication = [
            dict(ballot)
            for ballot in published
        ]

        for ballot in fake_publication:
            if ballot["id"] == voter.last_vote_id:
                ballot["candidate"] = next(
                    candidate
                    for candidate in self.candidates
                    if candidate != voter.last_candidate
                )
                break

        self.append_log(
            f"У копії опублікованих результатів змінюємо вибір для ID {voter.last_vote_id}."
        )

        self.run_and_capture(
            voter.verify_published_vote,
            fake_publication
        )

        self.refresh_state()
        self.refresh_results()

    def refresh_state(self):
        self.key_label.configure(
            text=f"Відкритий ключ ВК: {self.commission.public_key}"
        )

        for item in self.bureau_tree.get_children():
            self.bureau_tree.delete(item)

        for full_name, data in self.bureau.registered_voters.items():
            self.bureau_tree.insert(
                "",
                "end",
                values=(
                    full_name,
                    data["rn"],
                    str(data["public_key"])
                )
            )

        for item in self.commission_tree.get_children():
            self.commission_tree.delete(item)

        for rn, public_key in self.commission.registered_rns.items():
            status = (
                "використаний"
                if rn in self.commission.used_rns
                else "дійсний"
            )

            self.commission_tree.insert(
                "",
                "end",
                values=(
                    rn,
                    str(public_key),
                    status
                )
            )

    def refresh_results(self):
        results = self.commission.get_results()

        summary = "   ".join(
            f"{candidate}: {votes}"
            for candidate, votes in results.items()
        )

        self.results_summary.configure(
            text=summary
        )

        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        for ballot in self.commission.get_published_ballots():
            self.results_tree.insert(
                "",
                "end",
                values=(
                    ballot["id"],
                    ballot["candidate"],
                    ballot["signature"]
                )
            )

    def reset_system(self):
        self.create_system()

        self.log_text.configure(
            state="normal"
        )
        self.log_text.delete(
            "1.0",
            "end"
        )
        self.log_text.configure(
            state="disabled"
        )

        self.refresh_state()
        self.refresh_results()

        self.append_log(
            "Систему скинуто та ініціалізовано заново."
        )
        self.append_log(
            f"Відкритий ключ ВК: {self.commission.public_key}"
        )


def main():
    root = tk.Tk()
    VotingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
