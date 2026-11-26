import argparse
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from cert_resolver import CertificateResult, parse_lesson_url, verify_certificate_url


class CertificateApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Урок Цифры: Сертификат")
        self.root.geometry("640x290")
        self.root.resizable(False, False)

        self.url_var = tk.StringVar()
        self.slug_var = tk.StringVar()
        self.result_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Вставьте ссылку на тренажёр с параметром session_id.")

        self._build_ui()
        self._bind_hotkeys()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Ссылка на урок:").pack(anchor=tk.W)
        url_row = ttk.Frame(frame)
        url_row.pack(fill=tk.X, pady=(4, 10))

        self.url_entry = ttk.Entry(url_row, textvariable=self.url_var)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.url_entry.bind("<Return>", lambda _: self._start_resolve())

        ttk.Button(url_row, text="Вставить", command=self._paste_url).pack(side=tk.LEFT, padx=(8, 0))

        slug_row = ttk.Frame(frame)
        slug_row.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(slug_row, text="Код урока (необязательно):").pack(side=tk.LEFT)
        ttk.Entry(slug_row, textvariable=self.slug_var, width=28).pack(side=tk.LEFT, padx=(8, 0))

        action_row = ttk.Frame(frame)
        action_row.pack(fill=tk.X, pady=(0, 12))
        self.resolve_btn = ttk.Button(action_row, text="Получить сертификат", command=self._start_resolve)
        self.resolve_btn.pack(side=tk.LEFT)

        ttk.Label(frame, text="Ссылка на сертификат:").pack(anchor=tk.W)
        result_row = ttk.Frame(frame)
        result_row.pack(fill=tk.X, pady=(4, 10))

        self.result_entry = ttk.Entry(result_row, textvariable=self.result_var, state="readonly")
        self.result_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.copy_btn = ttk.Button(result_row, text="Копировать", command=self._copy_result, state=tk.DISABLED)
        self.copy_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.open_btn = ttk.Button(result_row, text="Открыть", command=self._open_result, state=tk.DISABLED)
        self.open_btn.pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(frame, textvariable=self.status_var, foreground="#444444", wraplength=600).pack(
            anchor=tk.W, pady=(6, 0)
        )

    def _bind_hotkeys(self) -> None:
        self.root.bind_class("TEntry", "<Control-KeyPress>", self._on_entry_ctrl_key)

    def _on_entry_ctrl_key(self, event: tk.Event) -> str | None:
        if event.keysym.lower() in ("a", "c", "v", "x"):
            return None

        widget = event.widget
        if event.keycode == 86:
            widget.event_generate("<<Paste>>")
            return "break"
        if event.keycode == 67:
            widget.event_generate("<<Copy>>")
            return "break"
        if event.keycode == 88:
            widget.event_generate("<<Cut>>")
            return "break"
        if event.keycode == 65:
            widget.select_range(0, tk.END)
            widget.icursor(tk.END)
            return "break"
        return None

    def _paste_url(self) -> None:
        try:
            clipboard = self.root.clipboard_get()
        except tk.TclError:
            return
        self.url_var.set(clipboard.strip())

    def _start_resolve(self) -> None:
        raw_url = self.url_var.get()
        slug_override = self.slug_var.get()

        try:
            target = parse_lesson_url(raw_url, slug_override)
        except ValueError as exc:
            messagebox.showerror("Ошибка ссылки", str(exc))
            return

        self.slug_var.set(target.slug)
        self.resolve_btn.config(state=tk.DISABLED)
        self.copy_btn.config(state=tk.DISABLED)
        self.open_btn.config(state=tk.DISABLED)
        self.result_var.set("")
        self.status_var.set("Проверяю страницу сертификата на сервере...")

        worker = threading.Thread(target=self._resolve_worker, args=(target,), daemon=True)
        worker.start()

    def _resolve_worker(self, target) -> None:
        try:
            result = verify_certificate_url(target)
        except RuntimeError as exc:
            self.root.after(0, self._on_error, str(exc))
            return
        self.root.after(0, self._on_success, result)

    def _on_success(self, result: CertificateResult) -> None:
        self.resolve_btn.config(state=tk.NORMAL)
        self.result_var.set(result.url)
        self.copy_btn.config(state=tk.NORMAL)
        self.open_btn.config(state=tk.NORMAL)
        self.status_var.set(f"Готово. Урок: {result.slug}. Можно открыть страницу и скачать сертификат.")

    def _on_error(self, message: str) -> None:
        self.resolve_btn.config(state=tk.NORMAL)
        self.status_var.set(message)
        messagebox.showerror("Ошибка проверки", message)

    def _copy_result(self) -> None:
        url = self.result_var.get()
        if not url:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        self.status_var.set("Ссылка скопирована в буфер обмена.")

    def _open_result(self) -> None:
        url = self.result_var.get()
        if url:
            webbrowser.open(url)


def run_cli(args: argparse.Namespace) -> int:
    try:
        target = parse_lesson_url(args.url, args.slug)
        result = verify_certificate_url(target)
    except (ValueError, RuntimeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1

    print(result.url)
    if args.open:
        webbrowser.open(result.url)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Получение ссылки на сертификат Урок Цифры.")
    parser.add_argument("url", nargs="?", help="Ссылка на урок с параметром session_id")
    parser.add_argument("--slug", default="", help="Переопределить код урока")
    parser.add_argument("--open", action="store_true", help="Открыть сертификат в браузере")
    args = parser.parse_args()

    if args.url:
        return run_cli(args)

    root = tk.Tk()
    CertificateApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
