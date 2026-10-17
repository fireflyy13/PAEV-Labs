import io
import contextlib
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from lab4 import Voter
from central_election_commission import (
    CentralElectionCommission,
    rsa_encrypt_number
)
from election_commission_1 import ElectionCommission1
from election_commission_2 import ElectionCommission2


class VotingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторна робота №4 — Розподіл бюлетеня")
        self.root.geometry("1280x820")
        self.root.minsize(1120, 700)

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
        self.refresh_all()

        self.append_log("Систему ініціалізовано.")
        self.append_log(f"Відкритий ключ ЦВК: {self.central.public_key}")
        self.append_log(
            "ID кандидатів: "
            + ", ".join(
                f"{candidate} = {candidate_id}"
                for candidate, candidate_id in self.central.candidate_ids.items()
            )
        )

    def create_system(self):
        self.voters = [
            Voter(name)
            for name in self.voter_names
        ]

        self.central = CentralElectionCommission(
            self.candidates
        )

        self.commission_1 = ElectionCommission1()
        self.commission_2 = ElectionCommission2()

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

        ttk.Label(
            main,
            text="Протокол Е-голосування з розділенням бюлетеня",
            style="Title.TLabel"
        ).pack(
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
            width=350
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
        ).pack(anchor="w")

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

        ttk.Label(
            selection,
            text="Кандидат:"
        ).pack(anchor="w")

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

        setup = ttk.LabelFrame(
            left,
            text="Підготовка",
            padding=10,
            style="Section.TLabelframe"
        )
        setup.pack(
            fill="x",
            pady=(0, 10)
        )

        self.make_button(
            setup,
            "Передати ключ виборця до ЦВК",
            self.register_selected_voter
        )

        self.make_button(
            setup,
            "Передати всі ключі до ЦВК",
            self.register_all_voters
        )

        self.make_button(
            setup,
            "Передати реєстр ЦВК → ВК-1 і ВК-2",
            self.transfer_registry
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
            "Проголосувати",
            self.vote
        )

        self.make_button(
            actions,
            "Об'єднати частини та підрахувати",
            self.combine_and_count
        )

        self.make_button(
            actions,
            "Перевірити публікації ВК-1 і ВК-2",
            self.verify_commission_publications
        )

        self.make_button(
            actions,
            "Перевірити відновлений бюлетень ЦВК",
            self.verify_central_publication
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
            "Незареєстрований виборець",
            self.test_unregistered_voter
        )

        self.make_button(
            tests,
            "Неправильний ЕЦП",
            self.test_wrong_signature
        )

        self.make_button(
            tests,
            "Підміна частини ВК-1",
            self.test_tampered_part
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
            text="Стан ЦВК і ВК"
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
        top = ttk.Frame(self.state_tab)
        top.pack(
            fill="x",
            pady=(0, 8)
        )

        self.key_label = ttk.Label(
            top,
            text=""
        )
        self.key_label.pack(anchor="w")

        self.candidates_label = ttk.Label(
            top,
            text=""
        )
        self.candidates_label.pack(
            anchor="w",
            pady=(3, 0)
        )

        voters_frame = ttk.LabelFrame(
            self.state_tab,
            text="ЦВК — список виборців та відкритих ключів",
            padding=8
        )
        voters_frame.pack(
            fill="both",
            expand=True,
            pady=(0, 8)
        )

        self.voters_tree = ttk.Treeview(
            voters_frame,
            columns=("voter", "key"),
            show="headings",
            height=5
        )

        self.voters_tree.heading(
            "voter",
            text="Виборець"
        )
        self.voters_tree.heading(
            "key",
            text="Відкритий ключ"
        )

        self.voters_tree.column(
            "voter",
            width=280
        )
        self.voters_tree.column(
            "key",
            width=300
        )

        self.voters_tree.pack(
            fill="both",
            expand=True
        )

        commissions = ttk.Frame(
            self.state_tab
        )
        commissions.pack(
            fill="both",
            expand=True
        )

        frame_1 = ttk.LabelFrame(
            commissions,
            text="ВК-1 — прийняті зашифровані частини",
            padding=8
        )
        frame_1.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 4)
        )

        frame_2 = ttk.LabelFrame(
            commissions,
            text="ВК-2 — прийняті зашифровані частини",
            padding=8
        )
        frame_2.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(4, 0)
        )

        self.commission_1_tree = ttk.Treeview(
            frame_1,
            columns=("id", "part"),
            show="headings"
        )
        self.commission_1_tree.heading(
            "id",
            text="ID виборця"
        )
        self.commission_1_tree.heading(
            "part",
            text="Зашифрована частина"
        )
        self.commission_1_tree.column(
            "id",
            width=160,
            anchor="center"
        )
        self.commission_1_tree.column(
            "part",
            width=180,
            anchor="center"
        )
        self.commission_1_tree.pack(
            fill="both",
            expand=True
        )

        self.commission_2_tree = ttk.Treeview(
            frame_2,
            columns=("id", "part"),
            show="headings"
        )
        self.commission_2_tree.heading(
            "id",
            text="ID виборця"
        )
        self.commission_2_tree.heading(
            "part",
            text="Зашифрована частина"
        )
        self.commission_2_tree.column(
            "id",
            width=160,
            anchor="center"
        )
        self.commission_2_tree.column(
            "part",
            width=180,
            anchor="center"
        )
        self.commission_2_tree.pack(
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
            columns=("id", "candidate_id", "candidate"),
            show="headings"
        )

        self.results_tree.heading(
            "id",
            text="ID виборця"
        )
        self.results_tree.heading(
            "candidate_id",
            text="Відновлений ID кандидата"
        )
        self.results_tree.heading(
            "candidate",
            text="Кандидат"
        )

        self.results_tree.column(
            "id",
            width=220,
            anchor="center"
        )
        self.results_tree.column(
            "candidate_id",
            width=220,
            anchor="center"
        )
        self.results_tree.column(
            "candidate",
            width=220,
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

    def is_registered_in_central(self, voter):
        return voter.full_name in self.central.voters

    def registry_loaded(self):
        return (
            bool(self.commission_1.voters)
            and bool(self.commission_2.voters)
        )

    def register_selected_voter(self):
        voter = self.selected_voter()

        self.section(
            f"Передача відкритого ключа до ЦВК: {voter.full_name}"
        )

        if self.is_registered_in_central(voter):
            self.append_log(
                "Виборець уже зареєстрований у ЦВК."
            )
            return

        self.central.register_voter(
            voter.full_name,
            voter.public_key
        )

        self.append_log(
            "Відкритий ключ виборця передано до ЦВК."
        )

        self.refresh_all()

    def register_all_voters(self):
        self.section(
            "Передача відкритих ключів усіх виборців до ЦВК"
        )

        for voter in self.voters:
            if not self.is_registered_in_central(voter):
                self.central.register_voter(
                    voter.full_name,
                    voter.public_key
                )

                self.append_log(
                    f"{voter.full_name}: відкритий ключ передано."
                )

        self.refresh_all()

    def transfer_registry(self):
        self.section(
            "Передача реєстру від ЦВК до ВК-1 та ВК-2"
        )

        registry = self.central.export_voter_registry()

        if not registry:
            self.append_log(
                "У ЦВК ще немає зареєстрованих виборців."
            )
            return

        self.run_and_capture(
            self.commission_1.load_voter_registry,
            registry
        )

        self.run_and_capture(
            self.commission_2.load_voter_registry,
            registry
        )

        self.refresh_all()

    def ensure_voter_ready(self, voter):
        if not self.is_registered_in_central(voter):
            self.central.register_voter(
                voter.full_name,
                voter.public_key
            )
            self.append_log(
                f"{voter.full_name}: відкритий ключ автоматично передано до ЦВК."
            )

        if (
            voter.full_name not in self.commission_1.voters
            or voter.full_name not in self.commission_2.voters
        ):
            registry = self.central.export_voter_registry()

            self.run_and_capture(
                self.commission_1.load_voter_registry,
                registry
            )

            self.run_and_capture(
                self.commission_2.load_voter_registry,
                registry
            )

    def vote(self):
        voter = self.selected_voter()
        candidate = self.candidate_var.get()

        self.section(
            f"Голосування: {voter.full_name} → {candidate}"
        )

        self.ensure_voter_ready(voter)

        if (
            voter.full_name in self.commission_1.received_voters
            or voter.full_name in self.commission_2.received_voters
        ):
            self.append_log(
                "Цей виборець уже надсилав частини бюлетеня."
            )
            return

        result = self.run_and_capture(
            voter.create_vote_messages,
            candidate,
            self.central.candidate_ids,
            self.central.public_key
        )

        if result is None:
            return

        message_1, message_2 = result

        self.append_log(
            f"ID виборця: {message_1['id']}"
        )
        self.append_log(
            f"ID кандидата {self.central.candidate_ids[candidate]} "
            f"поділено на множники "
            f"{voter.last_vote['factor_1']} і {voter.last_vote['factor_2']}."
        )
        self.append_log(
            "Обидві частини окремо зашифровано відкритим ключем ЦВК."
        )

        accepted_1 = self.run_and_capture(
            self.commission_1.receive_message,
            message_1["full_name"],
            message_1["id"],
            message_1["encrypted_part"],
            message_1["signature"]
        )

        accepted_2 = self.run_and_capture(
            self.commission_2.receive_message,
            message_2["full_name"],
            message_2["id"],
            message_2["encrypted_part"],
            message_2["signature"]
        )

        if accepted_1 and accepted_2:
            self.append_log(
                "Обидві частини бюлетеня успішно прийняті."
            )

        self.refresh_all()

    def combine_and_count(self):
        self.section(
            "Об'єднання зашифрованих частин та підрахунок"
        )

        publication_1 = self.commission_1.publish_data()
        publication_2 = self.commission_2.publish_data()

        if not publication_1 or not publication_2:
            self.append_log(
                "Для об'єднання потрібні опубліковані дані від обох ВК."
            )
            return

        self.append_log(
            "ЦВК спочатку множить відповідні зашифровані частини, "
            "а потім розшифровує вже об'єднаний шифротекст."
        )

        self.run_and_capture(
            self.central.process_publications,
            publication_1,
            publication_2
        )

        self.run_and_capture(
            self.central.publish_results
        )

        self.refresh_all()
        self.notebook.select(self.results_tab)

    def verify_commission_publications(self):
        voter = self.selected_voter()

        self.section(
            f"Перевірка публікацій ВК-1 та ВК-2: {voter.full_name}"
        )

        self.run_and_capture(
            voter.verify_commission_publications,
            self.commission_1.publish_data(),
            self.commission_2.publish_data()
        )

    def verify_central_publication(self):
        voter = self.selected_voter()

        self.section(
            f"Перевірка відновленого бюлетеня ЦВК: {voter.full_name}"
        )

        self.run_and_capture(
            voter.verify_central_publication,
            self.central.get_published_ballots()
        )

    def test_unregistered_voter(self):
        self.section(
            "Тест: незареєстрований виборець"
        )

        unknown = Voter(
            "Невідомий Виборець"
        )

        result = self.run_and_capture(
            unknown.create_vote_messages,
            self.candidates[0],
            self.central.candidate_ids,
            self.central.public_key
        )

        if result is None:
            return

        message_1, _ = result

        self.run_and_capture(
            self.commission_1.receive_message,
            message_1["full_name"],
            message_1["id"],
            message_1["encrypted_part"],
            message_1["signature"]
        )

        self.refresh_all()

    def test_wrong_signature(self):
        self.section(
            "Тест: неправильний ЕЦП"
        )

        test_voter = Voter(
            "Тестовий Виборець"
        )

        self.central.register_voter(
            test_voter.full_name,
            test_voter.public_key
        )

        test_commission = ElectionCommission1()

        self.run_and_capture(
            test_commission.load_voter_registry,
            self.central.export_voter_registry()
        )

        result = self.run_and_capture(
            test_voter.create_vote_messages,
            self.candidates[0],
            self.central.candidate_ids,
            self.central.public_key,
            None,
            1
        )

        if result is None:
            return

        message_1, _ = result

        self.run_and_capture(
            test_commission.receive_message,
            message_1["full_name"],
            message_1["id"],
            message_1["encrypted_part"],
            message_1["signature"]
        )

    def test_tampered_part(self):
        voter = self.selected_voter()

        self.section(
            "Тест: одна з ВК змінює свою частину бюлетеня"
        )

        if voter.last_vote is None:
            self.append_log(
                "Для тесту спочатку створюємо коректний голос вибраного виборця."
            )
            self.vote()

        if voter.last_vote is None:
            return

        publication_1 = [
            dict(item)
            for item in self.commission_1.publish_data()
        ]

        publication_2 = [
            dict(item)
            for item in self.commission_2.publish_data()
        ]

        target_id = voter.last_vote["id"]
        changed = False

        for item in publication_1:
            if item["id"] == target_id:
                item["encrypted_part"] = rsa_encrypt_number(
                    7,
                    self.central.public_key
                )
                changed = True
                break

        if not changed:
            self.append_log(
                "Частину вибраного виборця не знайдено у ВК-1."
            )
            return

        self.append_log(
            f"У копії публікації ВК-1 змінено зашифровану частину для ID {target_id}."
        )

        self.run_and_capture(
            self.central.process_publications,
            publication_1,
            publication_2
        )

        self.run_and_capture(
            voter.verify_commission_publications,
            publication_1,
            publication_2
        )

        self.append_log(
            "Після тесту відновлюємо результати з оригінальних публікацій."
        )

        self.run_and_capture(
            self.central.process_publications,
            self.commission_1.publish_data(),
            self.commission_2.publish_data()
        )

        self.refresh_all()

    def refresh_all(self):
        self.refresh_state()
        self.refresh_results()

    def refresh_state(self):
        self.key_label.configure(
            text=f"Відкритий ключ ЦВК: {self.central.public_key}"
        )

        self.candidates_label.configure(
            text="ID кандидатів: "
            + "   ".join(
                f"{candidate} = {candidate_id}"
                for candidate, candidate_id in self.central.candidate_ids.items()
            )
        )

        for item in self.voters_tree.get_children():
            self.voters_tree.delete(item)

        for full_name, public_key in self.central.voters.items():
            self.voters_tree.insert(
                "",
                "end",
                values=(
                    full_name,
                    str(public_key)
                )
            )

        for tree in [
            self.commission_1_tree,
            self.commission_2_tree
        ]:
            for item in tree.get_children():
                tree.delete(item)

        for item in self.commission_1.publish_data():
            self.commission_1_tree.insert(
                "",
                "end",
                values=(
                    item["id"],
                    item["encrypted_part"]
                )
            )

        for item in self.commission_2.publish_data():
            self.commission_2_tree.insert(
                "",
                "end",
                values=(
                    item["id"],
                    item["encrypted_part"]
                )
            )

    def refresh_results(self):
        results = self.central.get_results()

        summary = "   ".join(
            f"{candidate}: {votes}"
            for candidate, votes in results.items()
        )

        self.results_summary.configure(
            text=summary
        )

        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        for ballot in self.central.get_published_ballots():
            self.results_tree.insert(
                "",
                "end",
                values=(
                    ballot["id"],
                    ballot["candidate_id"],
                    ballot["candidate"]
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

        self.refresh_all()

        self.append_log(
            "Систему скинуто та ініціалізовано заново."
        )
        self.append_log(
            f"Відкритий ключ ЦВК: {self.central.public_key}"
        )
        self.append_log(
            "ID кандидатів: "
            + ", ".join(
                f"{candidate} = {candidate_id}"
                for candidate, candidate_id in self.central.candidate_ids.items()
            )
        )


def main():
    root = tk.Tk()
    VotingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
