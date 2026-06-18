"""Reusable DatePickerEntry widget.

Provides a small entry with a calendar popup implemented using standard
libraries only (datetime, calendar, tkinter) and CustomTkinter widgets.
"""
from __future__ import annotations

from typing import Optional, Callable
import logging
import calendar
import datetime
import tkinter as tk
import customtkinter as ctk

from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.utils import FONT_TERMINAL


logger = logging.getLogger(__name__)


class DatePickerEntry(ctk.CTkFrame):
    def __init__(
        self,
        master,
        module_name: Optional[str] = None,
        width: int = 140,
        allow_future: bool = False,
        command: Optional[Callable[[str], None]] = None,
        default_mode: Optional[str] = None, # 'today' or 'first_day_of_month'
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        try:
            self.module_name = module_name
            self.allow_future = bool(allow_future)
            self._command = command

            # Load palette
            try:
                self.colors = load_colors(module_name) or {}
            except Exception:
                logger.exception('Error loading colors for DatePickerEntry')
                self.colors = {}

            # Entry
            self._entry = ctk.CTkEntry(self, width=width)
            self._entry.configure(state='readonly')
            self._entry.pack(side='left', fill='x', expand=True)

            # Button
            self._btn = ctk.CTkButton(self, text='📅', width=36, height=28, command=self._open_calendar, font=FONT_TERMINAL)
            self._btn.pack(side='left', padx=(6, 0))

            # Internal state for calendar window
            self._cal_win: Optional[tk.Toplevel] = None
            today = datetime.date.today()
            self._year = today.year
            self._month = today.month

            # Aplicar valor por defecto si se solicita
            if default_mode == 'today':
                self.set(today.isoformat())
            elif default_mode == 'first_day_of_month':
                first_day = today.replace(day=1)
                self.set(first_day.isoformat())

        except Exception:
            logger.exception('Error initializing DatePickerEntry')

    # Public API
    def get(self) -> str:
        try:
            return self._entry.get().strip()
        except Exception:
            logger.exception('Error getting date from DatePickerEntry')
            return ''

    def set(self, date_str: str):
        try:
            # Validate format YYYY-MM-DD
            if not date_str:
                self.clear()
                return
            dt = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            if not self.allow_future and dt > datetime.date.today():
                return
            self._entry.configure(state='normal')
            self._entry.delete(0, 'end')
            self._entry.insert(0, dt.isoformat())
            self._entry.configure(state='readonly')
        except Exception:
            logger.exception('Error setting date in DatePickerEntry')

    def clear(self):
        try:
            self._entry.configure(state='normal')
            self._entry.delete(0, 'end')
            self._entry.configure(state='readonly')
        except Exception:
            logger.exception('Error clearing DatePickerEntry')

    # Private helpers
    def _open_calendar(self):
        try:
            if self._cal_win is not None:
                return

            root = self.winfo_toplevel()
            self._cal_win = tk.Toplevel(root)
            self._cal_win.wm_overrideredirect(True)
            try:
                self._cal_win.attributes('-topmost', True)
            except Exception:
                pass

            # Position below the entry
            try:
                x = self._entry.winfo_rootx()
                y = self._entry.winfo_rooty() + self._entry.winfo_height()
                self._cal_win.geometry(f'+{x}+{y}')
            except Exception:
                pass

            # Focus handling: close on focus out or Escape
            try:
                self._cal_win.bind('<FocusOut>', lambda e: self._close_calendar())
                self._cal_win.bind('<Escape>', lambda e: self._close_calendar())
            except Exception:
                pass

            # Build calendar UI
            self._build_calendar(self._year, self._month)

            # Ensure focus so FocusOut will work
            try:
                self._cal_win.focus_force()
            except Exception:
                pass

        except Exception:
            logger.exception('Error opening calendar')

    def _close_calendar(self):
        try:
            if self._cal_win:
                try:
                    self._cal_win.destroy()
                except Exception:
                    pass
            self._cal_win = None
        except Exception:
            logger.exception('Error closing calendar')

    def _build_calendar(self, year: int, month: int):
        try:
            # Clear previous content
            for child in list(self._cal_win.winfo_children()):
                try:
                    child.destroy()
                except Exception:
                    pass

            header = ctk.CTkFrame(self._cal_win, fg_color=self.colors.get('background', 'white'))
            header.pack(fill='x')

            prev_btn = ctk.CTkButton(header, text='<', width=28, command=lambda: self._navigate(-1))
            prev_btn.pack(side='left', padx=6, pady=6)

            month_lbl = ctk.CTkLabel(header, text=f'{calendar.month_name[month]} {year}', font=FONT_TERMINAL)
            month_lbl.pack(side='left', padx=8)

            next_btn = ctk.CTkButton(header, text='>', width=28, command=lambda: self._navigate(1))
            next_btn.pack(side='left', padx=6, pady=6)

            # Year selector
            years = list(range(datetime.date.today().year - 10, datetime.date.today().year + 6))
            year_vals = [str(y) for y in years]
            year_cb = ctk.CTkComboBox(header, values=year_vals, width=100)
            year_cb.set(str(year))
            year_cb.pack(side='right', padx=6)
            year_cb.configure(command=lambda v: self._on_year_selected(int(v)))

            cal_frame = ctk.CTkFrame(self._cal_win, fg_color=self.colors.get('background', 'white'))
            cal_frame.pack(fill='both', expand=True, padx=6, pady=6)

            # Weekday headers
            days = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']
            for c, d in enumerate(days):
                lbl = ctk.CTkLabel(cal_frame, text=d, font=('', 10))
                lbl.grid(row=0, column=c, padx=4, pady=2)

            month_cal = calendar.monthcalendar(year, month)
            today = datetime.date.today()

            for r, week in enumerate(month_cal, start=1):
                for c, day in enumerate(week):
                    if day == 0:
                        spacer = ctk.CTkLabel(cal_frame, text='')
                        spacer.grid(row=r, column=c, padx=2, pady=2)
                        continue
                    day_date = datetime.date(year, month, day)
                    disabled = (not self.allow_future) and (day_date > today)
                    if disabled:
                        btn = ctk.CTkButton(cal_frame, text=str(day), width=32, height=24, state='disabled')
                    else:
                        btn = ctk.CTkButton(cal_frame, text=str(day), width=32, height=24,
                                             command=lambda d=day: self._on_day_selected(year, month, d))
                    btn.grid(row=r, column=c, padx=2, pady=2)

        except Exception:
            logger.exception('Error building calendar UI')

    def _navigate(self, delta: int):
        try:
            # delta: -1 previous month, +1 next month
            m = self._month + delta
            y = self._year
            if m < 1:
                m = 12
                y -= 1
            elif m > 12:
                m = 1
                y += 1
            self._month = m
            self._year = y
            if self._cal_win:
                self._build_calendar(self._year, self._month)
        except Exception:
            logger.exception('Error navigating calendar')

    def _on_year_selected(self, year: int):
        try:
            self._year = int(year)
            if self._cal_win:
                self._build_calendar(self._year, self._month)
        except Exception:
            logger.exception('Error selecting year in calendar')

    def _on_day_selected(self, year: int, month: int, day: int):
        try:
            dt = datetime.date(year, month, day)
            if (not self.allow_future) and dt > datetime.date.today():
                return
            date_str = dt.isoformat()
            self.set(date_str)
            try:
                if callable(self._command):
                    self._command(date_str)
            except Exception:
                logger.exception('Error executing DatePickerEntry command')
            self._close_calendar()
        except Exception:
            logger.exception('Error handling day selection in calendar')
