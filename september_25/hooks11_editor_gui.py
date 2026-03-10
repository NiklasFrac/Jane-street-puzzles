#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pentomino Labs (GUI) v4 — Hooks in alle Richtungen (┌ ┐ └ ┘), Gruppenfarben, feste Leersetzungen

Änderung:
- BOARD_N ist jetzt wirklich variabel (z.B. 15 für 15x15).
- Ziffern/Clues unterstützen 1..BOARD_N (also auch 10..15 usw.).
  Eingabe: bei BOARD_N >= 10 einfach die Ziffern nacheinander tippen (z.B. 1 dann 5 → 15).
  '0' (wenn kein Zahleneingabe-Buffer aktiv ist) toggelt weiterhin ∅ wie zuvor.

Rest bleibt wie v4: Hooks (4 Orientierungen), Gruppenfarben, feste Leersetzungen, Setup/Test, Save/Load, Tastatursteuerung.
"""
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ---------------------------
# Konfiguration
# ---------------------------
# Anzahl Zellen pro Zeile/Spalte (z.B. 9, 12, 15, ...).
BOARD_N = 9

# Pixelgröße einer Zelle (bei großen BOARD_N evtl. kleiner stellen).
CELL = 44
MARGIN = 60

PENTO_TYPES = ["", "F", "I", "L", "N", "P", "T", "U", "V", "W", "X", "Y", "Z"]
VALID_CLUE_LETTERS = set(PENTO_TYPES[1:])
VALID_CLUE_DIGITS = set(str(d) for d in range(1, BOARD_N + 1))

HOOK_COLORS = ["#e53935", "#8e24aa", "#3949ab", "#1e88e5", "#00897b", "#7cb342", "#fdd835", "#fb8c00", "#6d4c41"]
ORIENTS = ["TL", "TR", "BL", "BR"]  # ┌ ┐ └ ┘


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Pentomino Labs – {BOARD_N}x{BOARD_N} Experiment (v4)")
        self.resizable(False, False)

        # Model
        self.grid_digits = [[0 for _ in range(BOARD_N)] for _ in range(BOARD_N)]
        self.grid_group  = [[0 for _ in range(BOARD_N)] for _ in range(BOARD_N)]
        self.group_type = {gid: "" for gid in range(1, 10)}
        self.given_mask = [[False for _ in range(BOARD_N)] for _ in range(BOARD_N)]  # fixed digits
        self.fixed_empty = [[False for _ in range(BOARD_N)] for _ in range(BOARD_N)] # fixed empties (0)

        # Außenhinweise
        self.clue_top    = ["" for _ in range(BOARD_N)]
        self.clue_bottom = ["" for _ in range(BOARD_N)]
        self.clue_left   = ["" for _ in range(BOARD_N)]
        self.clue_right  = ["" for _ in range(BOARD_N)]

        # Hooks store: list of dicts {id, n, r, c, orient, color}
        self.hooks = []
        self.next_hook_id = 1
        self.selected_hook_id = None

        # UI State
        self.mode = tk.StringVar(value="setup")  # "setup" | "test"
        self.show_groups = tk.BooleanVar(value=True)
        self.show_hooks = tk.BooleanVar(value=True)
        self.pending_group_input = False
        self.selected = None  # (r,c)

        # Hook tool state
        self.hook_size = tk.IntVar(value=3)
        self.hook_tool_enabled = tk.BooleanVar(value=False)
        self.hook_orient = tk.StringVar(value="TL")  # TL,TR,BL,BR — selected cell is the L-corner

        # Multi-digit digit input buffer (for BOARD_N >= 10)
        self._digit_buffer = ""
        self._digit_buffer_after = None
        self._digit_buffer_cell = None  # (r,c)

        # Build UI
        self._build_ui()
        self._bind_keys()
        self._redraw()

    # ---------------- UI ----------------
    def _build_ui(self):
        w = h = MARGIN * 2 + BOARD_N * CELL
        self.canvas = tk.Canvas(self, width=w, height=h, bg="#ffffff", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Button-3>", self._on_right_click)

        # Clue entries
        self.left_entries, self.right_entries = [], []
        self.top_entries, self.bottom_entries = [], []

        for c in range(BOARD_N):
            e = tk.Entry(self, width=4, justify="center")
            e.place(x=MARGIN + c * CELL + CELL / 2 - 14, y=8, width=28, height=24)
            self.top_entries.append(e)
            e = tk.Entry(self, width=4, justify="center")
            e.place(x=MARGIN + c * CELL + CELL / 2 - 14, y=MARGIN * 2 + BOARD_N * CELL - 32, width=28, height=24)
            self.bottom_entries.append(e)

        for r in range(BOARD_N):
            e = tk.Entry(self, width=4, justify="center")
            e.place(x=8, y=MARGIN + r * CELL + CELL / 2 - 12, width=28, height=24)
            self.left_entries.append(e)
            e = tk.Entry(self, width=4, justify="center")
            e.place(x=MARGIN * 2 + BOARD_N * CELL - 36, y=MARGIN + r * CELL + CELL / 2 - 12, width=28, height=24)
            self.right_entries.append(e)

        # Control panel
        panel = ttk.Frame(self)
        panel.grid(row=0, column=1, padx=12, pady=12, sticky="ns")

        # Modes
        ttk.Label(panel, text="Modus:").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(panel, text="Setup (Clues & Vorgaben)", variable=self.mode, value="setup", command=self._on_mode_change).grid(row=1, column=0, sticky="w")
        ttk.Radiobutton(panel, text="Test (Gedanken testen)", variable=self.mode, value="test", command=self._on_mode_change).grid(row=2, column=0, sticky="w")

        # Given controls
        gf = ttk.Frame(panel)
        gf.grid(row=3, column=0, sticky="we", pady=(6, 0))
        ttk.Button(gf, text="Aktuelle Ziffern fixieren (Vorgaben)", command=self._fix_givens_from_digits).grid(row=0, column=0, sticky="we")
        ttk.Button(gf, text="Vorgaben löschen", command=self._clear_givens).grid(row=1, column=0, sticky="we", pady=(4, 0))

        # Group & hooks toggles
        ttk.Checkbutton(panel, text="Pentominos farbig füllen (nach Gruppe)", variable=self.show_groups, command=self._redraw).grid(row=4, column=0, sticky="w")
        ttk.Checkbutton(panel, text="Hooks anzeigen (Umrandung)", variable=self.show_hooks, command=self._redraw).grid(row=5, column=0, sticky="w")

        # Hook tool
        ttk.Label(panel, text="Hook-Werkzeug:").grid(row=6, column=0, sticky="w", pady=(8, 0))
        hook_frame = ttk.Frame(panel)
        hook_frame.grid(row=7, column=0, sticky="we")
        ttk.Checkbutton(hook_frame, text="Aktivieren", variable=self.hook_tool_enabled).grid(row=0, column=0, sticky="w")
        ttk.Label(hook_frame, text="Größe n:").grid(row=0, column=1, padx=(8, 2))
        hs = ttk.Spinbox(hook_frame, from_=1, to=BOARD_N, width=3, textvariable=self.hook_size)
        hs.grid(row=0, column=2, sticky="w")
        # Orientation radios
        or_frame = ttk.Frame(hook_frame)
        or_frame.grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))
        ttk.Label(or_frame, text="Orientierung:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Radiobutton(or_frame, text="┌ TL", variable=self.hook_orient, value="TL").grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(or_frame, text="┐ TR", variable=self.hook_orient, value="TR").grid(row=0, column=2, sticky="w")
        ttk.Radiobutton(or_frame, text="└ BL", variable=self.hook_orient, value="BL").grid(row=0, column=3, sticky="w")
        ttk.Radiobutton(or_frame, text="┘ BR", variable=self.hook_orient, value="BR").grid(row=0, column=4, sticky="w")
        # Buttons
        ttk.Button(hook_frame, text="Hook hinzufügen (Ecke = Auswahl)", command=self._add_hook_at_selected).grid(row=2, column=0, columnspan=3, sticky="we", pady=(4, 0))
        ttk.Button(hook_frame, text="Hook löschen (an Auswahl)", command=self._delete_hook_at_selected).grid(row=3, column=0, columnspan=3, sticky="we")
        ttk.Button(hook_frame, text="Hook drehen (90°)", command=self._rotate_selected_hook).grid(row=4, column=0, columnspan=3, sticky="we")

        # Pentomino types per group
        ttk.Label(panel, text="Pentomino-Typ pro Gruppe:").grid(row=8, column=0, sticky="w", pady=(10, 0))
        self.group_type_vars = {}
        for g in range(1, 10):
            row = 8 + g
            ttk.Label(panel, text=f"Gruppe {g}:").grid(row=row, column=0, sticky="w")
            v = tk.StringVar(value="")
            cb = ttk.Combobox(panel, textvariable=v, values=PENTO_TYPES, width=4, state="readonly")
            cb.grid(row=row, column=0, sticky="e")
            cb.bind("<<ComboboxSelected>>", lambda e, gid=g: self._on_group_type_change(gid))
            self.group_type_vars[g] = v

        # Buttons
        btn_frame = ttk.Frame(panel)
        btn_frame.grid(row=18, column=0, pady=(10, 0), sticky="we")
        ttk.Button(btn_frame, text="Checks ausführen (Enter)", command=self._run_checks).grid(row=0, column=0, sticky="we")
        ttk.Button(btn_frame, text="Speichern… (S)", command=self._save).grid(row=1, column=0, sticky="we", pady=(6, 0))
        ttk.Button(btn_frame, text="Laden… (L)", command=self._load).grid(row=2, column=0, sticky="we")

        # Status
        self.status = tk.Text(panel, width=42, height=16, wrap="word", state="disabled")
        self.status.grid(row=19, column=0, pady=(12, 0))

        self._on_mode_change()

    def _bind_keys(self):
        self.bind("<Key>", self._on_key)
        self.bind("<Tab>", self._on_tab)
        self.bind("<ISO_Left_Tab>", self._on_shift_tab)
        self.bind("<Shift-Tab>", self._on_shift_tab)

    # ------------- Event Handlers -------------
    def _on_mode_change(self):
        mode = self.mode.get()
        state = "normal" if mode == "setup" else "disabled"
        for e in self.top_entries + self.bottom_entries + self.left_entries + self.right_entries:
            e.configure(state=state)
        self._redraw()

    def _fix_givens_from_digits(self):
        self._flush_digit_buffer()
        for r in range(BOARD_N):
            for c in range(BOARD_N):
                self.given_mask[r][c] = (self.grid_digits[r][c] != 0)
        messagebox.showinfo("Vorgaben", "Aktuelle Ziffern als Vorgaben markiert.\nIm Testmodus sind diese gesperrt.")
        self._redraw()

    def _clear_givens(self):
        self._flush_digit_buffer()
        self.given_mask = [[False for _ in range(BOARD_N)] for _ in range(BOARD_N)]
        self._redraw()

    def _on_group_type_change(self, gid):
        self.group_type[gid] = self.group_type_vars[gid].get()
        self._redraw()

    def _on_click(self, event):
        self._flush_digit_buffer()
        r = (event.y - MARGIN) // CELL
        c = (event.x - MARGIN) // CELL
        if 0 <= r < BOARD_N and 0 <= c < BOARD_N:
            self.selected = (r, c)
            if self.hook_tool_enabled.get():
                hid = self._hook_id_at_cell(r, c)
                self.selected_hook_id = hid
            self._redraw()

    def _on_right_click(self, event):
        self._flush_digit_buffer()
        r = (event.y - MARGIN) // CELL
        c = (event.x - MARGIN) // CELL
        if 0 <= r < BOARD_N and 0 <= c < BOARD_N:
            hid = self._hook_id_at_cell(r, c)
            if hid is not None:
                self.hooks = [h for h in self.hooks if h["id"] != hid]
                if self.selected_hook_id == hid:
                    self.selected_hook_id = None
                self._redraw()

    def _on_key(self, event):
        if event.keysym in ("Return", "KP_Enter"):
            self._flush_digit_buffer()
            self._run_checks()
            return "break"
        if event.char in ("s", "S"):
            self._flush_digit_buffer()
            self._save()
            return "break"
        if event.char in ("l", "L"):
            self._flush_digit_buffer()
            self._load()
            return "break"
        if event.char in ("t", "T"):
            self._flush_digit_buffer()
            self.mode.set("test"); self._on_mode_change()
            return "break"
        if event.char in ("u", "U"):
            self._flush_digit_buffer()
            self.mode.set("setup"); self._on_mode_change()
            return "break"

        if self.selected is None:
            self.selected = (0, 0)
        r, c = self.selected

        # Rotate selected hook
        if event.char in ("r", "R"):
            self._flush_digit_buffer()
            self._rotate_selected_hook()
            return "break"

        # Arrow keys
        if event.keysym in ("Left", "Right", "Up", "Down"):
            self._flush_digit_buffer()
            dr = dc = 0
            if event.keysym == "Left":
                dc = -1
            elif event.keysym == "Right":
                dc = 1
            elif event.keysym == "Up":
                dr = -1
            elif event.keysym == "Down":
                dr = 1
            nr, nc = r + dr, c + dc
            if 0 <= nr < BOARD_N and 0 <= nc < BOARD_N:
                self.selected = (nr, nc)
                if self.hook_tool_enabled.get():
                    self.selected_hook_id = self._hook_id_at_cell(nr, nc)
                self._redraw()
            return "break"

        # Delete / Backspace
        if event.keysym in ("BackSpace", "Delete"):
            self._flush_digit_buffer()
            if self.fixed_empty[r][c]:
                self.fixed_empty[r][c] = False
                self._redraw()
                return "break"
            if not (self.mode.get() == "test" and self.given_mask[r][c]):
                self.grid_digits[r][c] = 0
                self.given_mask[r][c] = False
            self._redraw()
            return "break"

        # Group mode
        if event.char in ("g", "G"):
            self._flush_digit_buffer()
            self.pending_group_input = True
            self._set_status("G-Modus: nächste Ziffer 0..9 setzt Gruppe (0=löschen).")
            return "break"

        # Digits (cell digits / buffer)
        if event.char and event.char.isdigit():
            ch = event.char

            # Group assignment stays 0..9 (wie vorher)
            if self.pending_group_input:
                d = int(ch)
                self.grid_group[r][c] = d if 1 <= d <= 9 else 0
                self.pending_group_input = False
                self._redraw()
                return "break"

            # '0' als Solo-Taste toggelt ∅ (wie vorher), nur wenn kein Zahl-Buffer aktiv ist
            if ch == "0" and self._digit_buffer == "":
                self._toggle_fixed_empty_at(r, c)
                self._redraw()
                return "break"

            self._append_digit_to_buffer(ch)
            return "break"

        return None

    def _on_tab(self, event):
        self._flush_digit_buffer()
        self._move_selection(0, 1)
        return "break"

    def _on_shift_tab(self, event):
        self._flush_digit_buffer()
        self._move_selection(0, -1)
        return "break"

    def _move_selection(self, dr, dc):
        if self.selected is None:
            self.selected = (0, 0)
        r, c = self.selected
        nc = c + dc
        nr = r + dr
        if nc >= BOARD_N:
            nc = 0
            nr = min(r + 1, BOARD_N - 1)
        if nc < 0:
            nc = BOARD_N - 1
            nr = max(r - 1, 0)
        nr = max(0, min(BOARD_N - 1, nr))
        self.selected = (nr, nc)
        if self.hook_tool_enabled.get():
            self.selected_hook_id = self._hook_id_at_cell(nr, nc)
        self._redraw()

    # ------------- Multi-digit digit input -------------
    def _append_digit_to_buffer(self, ch: str):
        if self.selected is None:
            self.selected = (0, 0)
        r, c = self.selected

        # Wechsel der Zelle -> alten Buffer committen
        if self._digit_buffer_cell is not None and self._digit_buffer_cell != (r, c):
            self._flush_digit_buffer()

        if self._digit_buffer_after is not None:
            try:
                self.after_cancel(self._digit_buffer_after)
            except Exception:
                pass
            self._digit_buffer_after = None

        self._digit_buffer_cell = (r, c)
        self._digit_buffer += ch

        max_len = max(1, len(str(BOARD_N)))

        # Wenn bereits zu lang, sofort flush (z.B. versehentlich 3 Ziffern bei N=15)
        if len(self._digit_buffer) >= max_len:
            self._flush_digit_buffer()
            return

        # Sonst nach kurzer Pause committen
        self._digit_buffer_after = self.after(650, self._flush_digit_buffer)

    def _flush_digit_buffer(self):
        if self._digit_buffer_after is not None:
            try:
                self.after_cancel(self._digit_buffer_after)
            except Exception:
                pass
        self._digit_buffer_after = None

        if not self._digit_buffer or self._digit_buffer_cell is None:
            self._digit_buffer = ""
            self._digit_buffer_cell = None
            return

        r, c = self._digit_buffer_cell
        s = self._digit_buffer
        self._digit_buffer = ""
        self._digit_buffer_cell = None

        # Sicherheitsnetz: leere / nicht parsebare Eingabe ignorieren
        try:
            val = int(s)
        except ValueError:
            return

        if val == 0:
            # 0 als Zahl wird hier nicht gebraucht; ∅ wird per Solo-'0' getoggelt
            return

        if not (1 <= val <= BOARD_N):
            # Out of range -> ignorieren
            return

        self._set_digit_at(r, c, val)
        self._redraw()

    def _set_digit_at(self, r: int, c: int, val: int):
        if self.mode.get() == "test" and (self.given_mask[r][c] or self.fixed_empty[r][c]):
            return
        self.grid_digits[r][c] = val
        self.given_mask[r][c] = False
        self.fixed_empty[r][c] = False

    def _toggle_fixed_empty_at(self, r: int, c: int):
        # identisches Verhalten wie zuvor (0 toggelt ∅), inkl. Sperre im Testmodus
        if self.mode.get() == "test" and self.fixed_empty[r][c]:
            return
        if self.grid_digits[r][c] == 0:
            self.fixed_empty[r][c] = not self.fixed_empty[r][c]
        else:
            if not (self.mode.get() == "test" and self.given_mask[r][c]):
                self.grid_digits[r][c] = 0
                self.given_mask[r][c] = False

    # ------------- Hooks -------------
    def _add_hook_at_selected(self):
        self._flush_digit_buffer()
        if self.selected is None:
            messagebox.showinfo("Hook", "Bitte zuerst eine Zelle im Gitter auswählen (Ecke des Hooks).")
            return
        r, c = self.selected
        n = int(self.hook_size.get())
        orient = self.hook_orient.get()  # TL,TR,BL,BR
        if not self._hook_fits(r, c, n, orient):
            messagebox.showerror("Hook", "Hook passt in dieser Orientierung/Größe hier nicht ins Gitter.")
            return
        hid = self.next_hook_id
        self.next_hook_id += 1
        color = HOOK_COLORS[(hid - 1) % len(HOOK_COLORS)]
        self.hooks.append({"id": hid, "n": n, "r": r, "c": c, "orient": orient, "color": color})
        self.selected_hook_id = hid
        self._redraw()

    def _delete_hook_at_selected(self):
        self._flush_digit_buffer()
        if self.selected is None:
            return
        r, c = self.selected
        hid = self._hook_id_at_cell(r, c)
        if hid is None:
            messagebox.showinfo("Hook", "Kein Hook an der ausgewählten Zelle.")
            return
        self.hooks = [h for h in self.hooks if h["id"] != hid]
        if self.selected_hook_id == hid:
            self.selected_hook_id = None
        self._redraw()

    def _rotate_selected_hook(self):
        self._flush_digit_buffer()
        if self.selected_hook_id is None:
            return
        for h in self.hooks:
            if h["id"] == self.selected_hook_id:
                idx = ORIENTS.index(h["orient"])
                for k in range(1, 5):
                    new_or = ORIENTS[(idx + k) % 4]
                    if self._hook_fits(h["r"], h["c"], h["n"], new_or):
                        h["orient"] = new_or
                        self._redraw()
                        return
                return

    def _hook_fits(self, r, c, n, orient):
        if n < 1 or n > BOARD_N:
            return False
        if orient == "TL":   # extends up and left
            return r - (n - 1) >= 0 and c - (n - 1) >= 0
        if orient == "TR":   # up and right
            return r - (n - 1) >= 0 and c + (n - 1) < BOARD_N
        if orient == "BL":   # down and left
            return r + (n - 1) < BOARD_N and c - (n - 1) >= 0
        if orient == "BR":   # down and right
            return r + (n - 1) < BOARD_N and c + (n - 1) < BOARD_N
        return False

    def _hook_cells(self, hook):
        n = hook["n"]
        r = hook["r"]
        c = hook["c"]
        orient = hook["orient"]
        cells = {(r, c)}
        if orient == "TL":
            for k in range(1, n):
                cells.add((r - k, c))
            for k in range(1, n):
                cells.add((r, c - k))
        elif orient == "TR":
            for k in range(1, n):
                cells.add((r - k, c))
            for k in range(1, n):
                cells.add((r, c + k))
        elif orient == "BL":
            for k in range(1, n):
                cells.add((r + k, c))
            for k in range(1, n):
                cells.add((r, c - k))
        elif orient == "BR":
            for k in range(1, n):
                cells.add((r + k, c))
            for k in range(1, n):
                cells.add((r, c + k))
        return cells

    def _hook_id_at_cell(self, rr, cc):
        for h in self.hooks:
            if (rr, cc) in self._hook_cells(h):
                return h["id"]
        return None

    def _draw_hooks(self):
        for h in self.hooks:
            cells = self._hook_cells(h)
            color = h["color"]
            width = 3 if h["id"] == self.selected_hook_id else 2
            for (r, c) in cells:
                x = MARGIN + c * CELL
                y = MARGIN + r * CELL
                if (r - 1, c) not in cells:
                    self.canvas.create_line(x, y, x + CELL, y, fill=color, width=width)
                if (r + 1, c) not in cells:
                    self.canvas.create_line(x, y + CELL, x + CELL, y + CELL, fill=color, width=width)
                if (r, c - 1) not in cells:
                    self.canvas.create_line(x, y, x, y + CELL, fill=color, width=width)
                if (r, c + 1) not in cells:
                    self.canvas.create_line(x + CELL, y, x + CELL, y + CELL, fill=color, width=width)

    # ------------- Drawing -------------
    def _redraw(self):
        self.canvas.delete("all")
        w = h = MARGIN * 2 + BOARD_N * CELL
        self.canvas.create_rectangle(0, 0, w, h, fill="#ffffff", outline="")

        # Labels
        self.canvas.create_text(MARGIN + BOARD_N * CELL / 2, 24, text=f"TOP (1-{BOARD_N} oder F/I/L/N/P/T/U/V/W/X/Y/Z)", font=("Segoe UI", 9))
        self.canvas.create_text(MARGIN + BOARD_N * CELL / 2, MARGIN * 2 + BOARD_N * CELL - 16, text="BOTTOM", font=("Segoe UI", 9))
        self.canvas.create_text(46, MARGIN + BOARD_N * CELL / 2, text="LEFT", angle=90, font=("Segoe UI", 9))
        self.canvas.create_text(MARGIN * 2 + BOARD_N * CELL - 16, MARGIN + BOARD_N * CELL / 2, text="RIGHT", angle=270, font=("Segoe UI", 9))

        # Grid lines
        for i in range(BOARD_N + 1):
            x0 = MARGIN + i * CELL
            y0 = MARGIN
            x1 = x0
            y1 = MARGIN + BOARD_N * CELL
            self.canvas.create_line(x0, y0, x1, y1, fill="#444" if i % 3 == 0 else "#aaa")
            x0 = MARGIN
            y0 = MARGIN + i * CELL
            x1 = MARGIN + BOARD_N * CELL
            y1 = y0
            self.canvas.create_line(x0, y0, x1, y1, fill="#444" if i % 3 == 0 else "#aaa")

        # Read clues
        self._pull_clues_from_entries()

        # Group-based background fill (optional)
        if self.show_groups.get():
            for r in range(BOARD_N):
                for c in range(BOARD_N):
                    g = self.grid_group[r][c]
                    if g != 0:
                        hue = (g * 37) % 360
                        color = self._hsl_to_hex(hue, 0.65, 0.90)
                        x = MARGIN + c * CELL
                        y = MARGIN + r * CELL
                        self.canvas.create_rectangle(x + 1, y + 1, x + CELL - 1, y + CELL - 1, fill=color, outline="")

        # Digits & overlays
        for r in range(BOARD_N):
            for c in range(BOARD_N):
                x = MARGIN + c * CELL
                y = MARGIN + r * CELL
                d = self.grid_digits[r][c]
                g = self.grid_group[r][c]

                if d != 0:
                    # Font automatisch etwas kleiner bei 2+ Stellen
                    base = 16 if BOARD_N <= 9 else 14
                    shrink = max(0, len(str(d)) - 1) * 2
                    size = max(10, base - shrink)
                    self.canvas.create_text(x + CELL / 2, y + CELL / 2, text=str(d), font=("Segoe UI", size, "bold"))

                if g != 0:
                    self.canvas.create_text(x + CELL - 8, y + 10, text=str(g), font=("Segoe UI", 9))
                if self.mode.get() == "test" and d != 0 and self.given_mask[r][c]:
                    self.canvas.create_text(x + 10, y + 10, text="🔒", font=("Segoe UI Emoji", 10))
                if self.fixed_empty[r][c] and d == 0:
                    self.canvas.create_text(x + CELL / 2, y + CELL / 2, text="∅", font=("Segoe UI", 14))

        # Hooks
        if self.show_hooks.get():
            self._draw_hooks()

        # Selection highlight
        if self.selected is not None:
            r, c = self.selected
            x = MARGIN + c * CELL
            y = MARGIN + r * CELL
            self.canvas.create_rectangle(x + 2, y + 2, x + CELL - 2, y + CELL - 2, outline="#ff5a00", width=2)

    # ------------- Checks -------------
    def _run_checks(self):
        self._pull_clues_from_entries()
        issues = []

        # 2×2
        bad_2x2 = self._find_full_2x2_blocks()
        if bad_2x2:
            issues.append(f" 2x2 voll gefüllt an: {bad_2x2[:5]}{' …' if len(bad_2x2) > 5 else ''}")
        else:
            issues.append(" Kein 2x2-Block ist komplett gefüllt.")

        # Connectivity (filled)
        connected, total, comp = self._is_filled_connected()
        if total == 0:
            issues.append(" Noch keine gefüllten Zellen - Konnektivität nicht geprüft.")
        elif connected:
            issues.append(f" Gefüllte Zellen sind zusammenhängend (Anzahl={total}).")
        else:
            issues.append(f" Gefüllte Zellen sind NICHT zusammenhängend (Komponenten={comp}).")

        # Digit counts
        counts = {d: 0 for d in range(1, BOARD_N + 1)}
        for r in range(BOARD_N):
            for c in range(BOARD_N):
                d = self.grid_digits[r][c]
                if 1 <= d <= BOARD_N:
                    counts[d] += 1
        counts_msg = " / ".join(f"{d}:{counts[d]}" for d in range(BOARD_N, 0, -1))
        issues.append(f" Ziffernbelegung (soll: {BOARD_N}x{BOARD_N}, {BOARD_N-1}x{BOARD_N-1}, …, 1x1): {counts_msg}")

        # Groups
        group_cells = self._collect_groups()
        used_groups = sorted(g for g, cells in group_cells.items() if cells)
        if not used_groups:
            issues.append(" Keine Gruppen zugewiesen.")
        else:
            assigned_types = [self.group_type[g] for g in used_groups if self.group_type[g]]
            dups = self._find_duplicates(assigned_types)
            if dups:
                issues.append(f" Pentomino-Typen nicht eindeutig (Mehrfach: {', '.join(sorted(dups))}).")
            else:
                issues.append(" Zuweisungen der Pentomino-Typen (sofern gesetzt) sind eindeutig.")
            for g in used_groups:
                cells = group_cells[g]
                if len(cells) != 5:
                    issues.append(f" Gruppe {g}: hat {len(cells)} Zellen (muss 5 haben).")
                else:
                    issues.append(f" Gruppe {g}: hat 5 Zellen.")
                if cells and not self._is_set_connected(cells):
                    issues.append(f" Gruppe {g}: Zellen sind nicht zusammenhängend.")
                s = sum(self.grid_digits[r][c] for (r, c) in cells)
                if s % 5 != 0:
                    issues.append(f" Gruppe {g}: Summe={s} (muss ≡ 0 (mod 5)).")
                else:
                    issues.append(f" Gruppe {g}: Summe={s} ≡ 0 (mod 5).")
                if not self.group_type[g]:
                    issues.append(f" Gruppe {g}: Pentomino-Typ noch nicht gesetzt (freiwillig).")

        # Edge clues
        clue_issues = self._check_first_seen_clues()
        issues.extend(clue_issues)

        # Hook overlaps (info)
        overlaps = self._find_hook_overlaps()
        if overlaps:
            issues.append(f" Hooks überlappen sich in {len(overlaps)} Zellen (visuelle Hilfe; Partition ggf. verlangt).")
        else:
            issues.append(" Hooks: keine Überlappungen gefunden (Hinweis: Partition nicht automatisch erzwungen).")

        self._set_status("\n".join(issues))

    # ------------- Logic Utils -------------
    def _pull_clues_from_entries(self):
        def norm(s):
            s = s.strip().upper()
            if not s:
                return ""
            # Akzeptiert jetzt 1..BOARD_N (auch zweistellig) oder Pentomino-Buchstaben
            if s in VALID_CLUE_DIGITS or s in VALID_CLUE_LETTERS:
                return s
            return s
        for c in range(BOARD_N):
            self.clue_top[c] = norm(self.top_entries[c].get())
            self.clue_bottom[c] = norm(self.bottom_entries[c].get())
        for r in range(BOARD_N):
            self.clue_left[r] = norm(self.left_entries[r].get())
            self.clue_right[r] = norm(self.right_entries[r].get())

    def _find_full_2x2_blocks(self):
        bad = []
        for r in range(BOARD_N - 1):
            for c in range(BOARD_N - 1):
                if all(self.grid_digits[r + dr][c + dc] != 0 for dr in (0, 1) for dc in (0, 1)):
                    bad.append((r, c))
        return bad

    def _neighbors4(self, r, c):
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < BOARD_N and 0 <= cc < BOARD_N:
                yield rr, cc

    def _is_filled_connected(self):
        nodes = [(r, c) for r in range(BOARD_N) for c in range(BOARD_N) if self.grid_digits[r][c] != 0]
        if not nodes:
            return False, 0, 0
        seen = set()
        from collections import deque
        q = deque([nodes[0]])
        seen.add(nodes[0])
        while q:
            r, c = q.popleft()
            for rr, cc in self._neighbors4(r, c):
                if self.grid_digits[rr][cc] != 0 and (rr, cc) not in seen:
                    seen.add((rr, cc))
                    q.append((rr, cc))
        if len(seen) == len(nodes):
            return True, len(nodes), 1
        return False, len(nodes), self._count_components(nodes)

    def _count_components(self, nodes):
        nodes = set(nodes)
        seen = set()
        comps = 0
        from collections import deque
        for start in nodes:
            if start in seen:
                continue
            comps += 1
            q = deque([start])
            seen.add(start)
            while q:
                r, c = q.popleft()
                for rr, cc in self._neighbors4(r, c):
                    if (rr, cc) in nodes and (rr, cc) not in seen and self.grid_digits[rr][cc] != 0:
                        seen.add((rr, cc))
                        q.append((rr, cc))
        return comps

    def _collect_groups(self):
        groups = {g: set() for g in range(1, 10)}
        for r in range(BOARD_N):
            for c in range(BOARD_N):
                g = self.grid_group[r][c]
                if 1 <= g <= 9 and self.grid_digits[r][c] != 0:
                    groups[g].add((r, c))
        return groups

    def _is_set_connected(self, cells):
        if not cells:
            return True
        cells = set(cells)
        from collections import deque
        start = next(iter(cells))
        q = deque([start])
        seen = {start}
        while q:
            r, c = q.popleft()
            for rr, cc in self._neighbors4(r, c):
                if (rr, cc) in cells and (rr, cc) not in seen:
                    seen.add((rr, cc))
                    q.append((rr, cc))
        return len(seen) == len(cells)

    def _find_duplicates(self, items):
        from collections import Counter
        c = Counter(items)
        return [k for k, v in c.items() if v > 1]

    def _check_first_seen_clues(self):
        msgs = []
        # Top
        for c in range(BOARD_N):
            clue = self.clue_top[c]
            if clue:
                pos = self._first_filled_in_col_from_top(c)
                msgs += self._check_first_seen("TOP", f"Spalte {c + 1}", clue, pos)
        # Bottom
        for c in range(BOARD_N):
            clue = self.clue_bottom[c]
            if clue:
                pos = self._first_filled_in_col_from_bottom(c)
                msgs += self._check_first_seen("BOTTOM", f"Spalte {c + 1}", clue, pos)
        # Left
        for r in range(BOARD_N):
            clue = self.clue_left[r]
            if clue:
                pos = self._first_filled_in_row_from_left(r)
                msgs += self._check_first_seen("LEFT", f"Zeile {r + 1}", clue, pos)
        # Right
        for r in range(BOARD_N):
            clue = self.clue_right[r]
            if clue:
                pos = self._first_filled_in_row_from_right(r)
                msgs += self._check_first_seen("RIGHT", f"Zeile {r + 1}", clue, pos)
        return msgs

    def _first_filled_in_row_from_left(self, r):
        for c in range(BOARD_N):
            if self.grid_digits[r][c] != 0:
                return (r, c)
        return None

    def _first_filled_in_row_from_right(self, r):
        for c in range(BOARD_N - 1, -1, -1):
            if self.grid_digits[r][c] != 0:
                return (r, c)
        return None

    def _first_filled_in_col_from_top(self, c):
        for r in range(BOARD_N):
            if self.grid_digits[r][c] != 0:
                return (r, c)
        return None

    def _first_filled_in_col_from_bottom(self, c):
        for r in range(BOARD_N - 1, -1, -1):
            if self.grid_digits[r][c] != 0:
                return (r, c)
        return None

    def _check_first_seen(self, side, label, clue, pos):
        msgs = []
        if clue in VALID_CLUE_DIGITS:
            if pos is None:
                msgs.append(f" {side} {label}: erwartet erste Ziffer {clue}, aber noch keine belegte Zelle in Sichtlinie.")
            else:
                r, c = pos
                val = self.grid_digits[r][c]
                if str(val) == clue:
                    msgs.append(f" {side} {label}: erste Ziffer = {clue}.")
                else:
                    msgs.append(f" {side} {label}: erste Ziffer ist {val}, erwartet {clue}.")
        elif clue in VALID_CLUE_LETTERS:
            if pos is None:
                msgs.append(f" {side} {label}: erwartet erster Pentomino-Typ {clue}, aber noch keine belegte Zelle.")
            else:
                r, c = pos
                gid = self.grid_group[r][c]
                if gid == 0:
                    msgs.append(f" {side} {label}: erste belegte Zelle hat keine Gruppe (Typ unbekannt), erwartet {clue}.")
                else:
                    gt = self.group_type.get(gid, "")
                    if not gt:
                        msgs.append(f" {side} {label}: Gruppe {gid} hat noch keinen Typ; erwartet {clue}.")
                    elif gt == clue:
                        msgs.append(f" {side} {label}: erster Pentomino-Typ = {clue}.")
                    else:
                        msgs.append(f" {side} {label}: erster Pentomino-Typ ist {gt} (Gruppe {gid}), erwartet {clue}.")
        else:
            msgs.append(f" {side} {label}: unbekannter Hinweis „{clue}“.")
        return msgs

    # -------- Hook diagnostics --------
    def _find_hook_overlaps(self):
        seen = {}
        overlaps = []
        for h in self.hooks:
            for cell in self._hook_cells(h):
                if cell in seen:
                    overlaps.append(cell)
                else:
                    seen[cell] = h["id"]
        return overlaps

    # ------------- Save/Load -------------
    def _state_dict(self):
        return {
            "board_n": BOARD_N,
            "grid_digits": self.grid_digits,
            "grid_group": self.grid_group,
            "group_type": self.group_type,
            "given_mask": self.given_mask,
            "fixed_empty": self.fixed_empty,
            "mode": self.mode.get(),
            "clue_top": self.clue_top,
            "clue_bottom": self.clue_bottom,
            "clue_left": self.clue_left,
            "clue_right": self.clue_right,
            "hooks": self.hooks,
            "next_hook_id": self.next_hook_id,
        }

    def _apply_state(self, state):
        # NOTE: lädt 1:1; bei abweichendem BOARD_N kann es inkonsistent sein.
        self.grid_digits = state.get("grid_digits", self.grid_digits)
        self.grid_group  = state.get("grid_group", self.grid_group)
        self.group_type  = {int(k): v for k, v in state.get("group_type", self.group_type).items()}
        self.given_mask  = state.get("given_mask", self.given_mask)
        self.fixed_empty = state.get("fixed_empty", self.fixed_empty)
        self.mode.set(state.get("mode", "setup"))
        self.clue_top    = state.get("clue_top", self.clue_top)
        self.clue_bottom = state.get("clue_bottom", self.clue_bottom)
        self.clue_left   = state.get("clue_left", self.clue_left)
        self.clue_right  = state.get("clue_right", self.clue_right)
        self.hooks       = state.get("hooks", self.hooks)
        self.next_hook_id = state.get("next_hook_id", self.next_hook_id)
        # reflect UI
        for g in range(1, 10):
            v = self.group_type.get(g, "")
            self.group_type_vars[g].set(v)
        for c in range(BOARD_N):
            self.top_entries[c].configure(state="normal");    self.top_entries[c].delete(0, "end"); self.top_entries[c].insert(0, self.clue_top[c])
            self.bottom_entries[c].configure(state="normal"); self.bottom_entries[c].delete(0, "end"); self.bottom_entries[c].insert(0, self.clue_bottom[c])
        for r in range(BOARD_N):
            self.left_entries[r].configure(state="normal");   self.left_entries[r].delete(0, "end"); self.left_entries[r].insert(0, self.clue_left[r])
            self.right_entries[r].configure(state="normal");  self.right_entries[r].delete(0, "end"); self.right_entries[r].insert(0, self.clue_right[r])
        self._on_mode_change()
        self._redraw()

    def _save(self):
        self._flush_digit_buffer()
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"pentomino_state_v4_{BOARD_N}x{BOARD_N}.json",
            title="Zustand speichern",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._state_dict(), f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Gespeichert", f"Zustand gespeichert:\n{path}")

    def _load(self):
        self._flush_digit_buffer()
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Zustand laden",
        )
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        self._apply_state(state)
        messagebox.showinfo("Geladen", f"Zustand geladen:\n{path}")

    def _set_status(self, text):
        self.status.configure(state="normal")
        self.status.delete("1.0", "end")
        self.status.insert("end", text)
        self.status.configure(state="disabled")

    # ------------- Utility -------------
    @staticmethod
    def _hsl_to_hex(h, s, l):
        c = (1 - abs(2 * l - 1)) * s
        hp = h / 60.0
        x = c * (1 - abs(hp % 2 - 1))
        r = g = b = 0
        if 0 <= hp < 1:
            r, g, b = c, x, 0
        elif 1 <= hp < 2:
            r, g, b = x, c, 0
        elif 2 <= hp < 3:
            r, g, b = 0, c, x
        elif 3 <= hp < 4:
            r, g, b = 0, x, c
        elif 4 <= hp < 5:
            r, g, b = x, 0, c
        elif 5 <= hp < 6:
            r, g, b = c, 0, x
        m = l - c / 2
        r, g, b = (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))
        return f"#{r:02x}{g:02x}{b:02x}"


if __name__ == "__main__":
    App().mainloop()