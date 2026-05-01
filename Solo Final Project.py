import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime


DB_FILE = "freelance.db"

class MyFreelanceApp:
    def __init__(self, window):
        self.win = window
        self.win.title("Freelance Tracker")
        self.win.geometry("980x720")

        # Set up the DB first-thing
        self.start_up_db()

        # Build UI
        self.tabs = ttk.Notebook(self.win)
        self.tabs.pack(expand=1, fill="both")

        # These are the tab frames; three should be sufficient
        self.pg1 = ttk.Frame(self.tabs)
        self.pg2 = ttk.Frame(self.tabs)
        self.pg3 = ttk.Frame(self.tabs)

        self.tabs.add(self.pg1, text="Client List")
        self.tabs.add(self.pg2, text="Log Hours")
        self.tabs.add(self.pg3, text="Pay & Reports")

        # Call builders
        self.make_client_screen()
        self.make_logger_screen()
        self.make_report_screen()

    def start_up_db(self):
        db_conn = sqlite3.connect(DB_FILE)
        cursor = db_conn.cursor()
        
        # Table 1
        cursor.execute('''CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            hourly_rate REAL NOT NULL,
            contact TEXT,
            active INTEGER DEFAULT 1)''')
        
        # Table 2 with the FK inside the CREATE
        cursor.execute('''CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            hours REAL NOT NULL,
            description TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id))''')
        
        db_conn.commit()
        db_conn.close()

    def make_client_screen(self):
        add_frame = tk.LabelFrame(self.pg1, text=" Register New Client ")
        add_frame.pack(padx=20, pady=20, fill="x")

        tk.Label(add_frame, text="Name:").grid(row=0, column=0, padx=5, pady=10)
        self.input_name = tk.Entry(add_frame)
        self.input_name.grid(row=0, column=1)

        tk.Label(add_frame, text="Rate ($):").grid(row=0, column=2, padx=5)
        self.input_rate = tk.Entry(add_frame, width=10)
        self.input_rate.grid(row=0, column=3)

        tk.Label(add_frame, text="Contact Info:").grid(row=0, column=4, padx=5)
        self.input_contact = tk.Entry(add_frame)
        self.input_contact.grid(row=0, column=5)

        tk.Button(add_frame, text="Save to DB", command=self.save_new_client).grid(row=0, column=6, padx=15)

        # List view
        self.client_box = ttk.Treeview(self.pg1, columns=("id", "n", "r", "s"), show="headings")
        self.client_box.heading("id", text="ID")
        self.client_box.heading("n", text="Client Name")
        self.client_box.heading("r", text="Rate")
        self.client_box.heading("s", text="Status")
        self.client_box.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.reload_client_list()

    def save_new_client(self):
        n = self.input_name.get()
        r = self.input_rate.get()
        c = self.input_contact.get()
        
        if n == "" or r == "":
            messagebox.showwarning("Error", "Need a name and a rate!")
            return
            
        try:
            val_rate = float(r)
            db = sqlite3.connect(DB_FILE)
            db.execute("INSERT INTO clients (name, hourly_rate, contact) VALUES (?,?,?)", (n, val_rate, c))
            db.commit()
            db.close()
            # Refresh stuff
            self.reload_client_list()
            self.fix_dropdowns()
            # Clear entries
            self.input_name.delete(0, 'end')
            self.input_rate.delete(0, 'end')
            self.input_contact.delete(0, 'end')
        except Exception as e:
            messagebox.showerror("Fail", f"Couldnt save: {e}")

    def reload_client_list(self):
        for i in self.client_box.get_children():
            self.client_box.delete(i)
        db = sqlite3.connect(DB_FILE)
        data = db.execute("SELECT id, name, hourly_rate, active FROM clients").fetchall()
        for d in data:
            st = "Active" if d[3] == 1 else "Inactive"
            self.client_box.insert("", "end", values=(d[0], d[1], f"${d[2]}", st))
        db.close()

    def make_logger_screen(self):
        # Logger input
        top = tk.LabelFrame(self.pg2, text=" Work Session Entry ")
        top.pack(fill="x", padx=10, pady=10)

        tk.Label(top, text="Client:").grid(row=0, column=0, pady=10)
        self.client_choice = ttk.Combobox(top, state="readonly")
        self.client_choice.grid(row=0, column=1)

        tk.Label(top, text="Date (YYYY-MM-DD):").grid(row=0, column=2)
        self.date_field = tk.Entry(top)
        self.date_field.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_field.grid(row=0, column=3)

        tk.Label(top, text="Hours:").grid(row=1, column=0, pady=10)
        self.hour_field = tk.Entry(top)
        self.hour_field.grid(row=1, column=1)

        tk.Label(top, text="Description:").grid(row=1, column=2)
        self.work_desc = tk.Entry(top)
        self.work_desc.grid(row=1, column=3, sticky="ew")

        tk.Button(top, text="Log Session", bg="lightgreen", command=self.submit_hours).grid(row=1, column=4, padx=10)

        # Filteras
        f_frame = tk.Frame(self.pg2)
        f_frame.pack(fill="x", padx=10)
        tk.Label(f_frame, text="View:").pack(side="left")
        self.filter_choice = ttk.Combobox(f_frame, state="readonly")
        self.filter_choice.pack(side="left", padx=5)
        tk.Button(f_frame, text="Filter", command=self.reload_sessions).pack(side="left")
        
        # Delete button
        tk.Button(f_frame, text="Delete Selected", command=self.delete_session).pack(side="right")

        cols = ("date", "client", "hrs", "pay", "desc")
        self.session_view = ttk.Treeview(self.pg2, columns=cols, show="headings")
        for c in cols: self.session_view.heading(c, text=c.capitalize())
        self.session_view.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.fix_dropdowns()
        self.reload_sessions()

    def submit_hours(self):
        c = self.client_choice.get()
        d = self.date_field.get()
        h = self.hour_field.get()
        note = self.work_desc.get()

        # Validation logic
        try:
            datetime.strptime(d, "%Y-%m-%d") 
            hrs = float(h)
            if hrs <= 0: raise ValueError("Positive hours only!")
        except Exception:
            messagebox.showerror("Input Error", "Check your date (YYYY-MM-DD) or Hours (must be > 0)!")
            return

        db = sqlite3.connect(DB_FILE)
        # get the ID for the client name
        cid = db.execute("SELECT id FROM clients WHERE name=?", (c,)).fetchone()[0]
        db.execute("INSERT INTO sessions (client_id, date, hours, description) VALUES (?,?,?,?)", (cid, d, hrs, note))
        db.commit()
        db.close()
        
        self.reload_sessions()
        self.hour_field.delete(0, 'end')

    def reload_sessions(self):
        for i in self.session_view.get_children(): self.session_view.delete(i)
        
        filt = self.filter_choice.get()
        sql = "SELECT s.date, c.name, s.hours, (s.hours * c.hourly_rate) as earnings, s.description FROM sessions s JOIN clients c ON s.client_id = c.id"
        
        db = sqlite3.connect(DB_FILE)
        if filt != "All Clients" and filt != "":
            data = db.execute(sql + " WHERE c.name = ?", (filt,)).fetchall()
        else:
            data = db.execute(sql).fetchall()
        
        for r in data:
           
            self.session_view.insert("", "end", values=(r[0], r[1], r[2], f"${r[3]:.2f}", r[4]))
        db.close()

    def delete_session(self):
        selected = self.session_view.selection()[0] 
        row_vals = self.session_view.item(selected)['values']
        
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete session for {row_vals[1]}?"):
            # Find the id. ID not in tree- match by date/client/desc
            db = sqlite3.connect(DB_FILE)
            db.execute("DELETE FROM sessions WHERE date=? AND description=?", (row_vals[0], row_vals[4]))
            db.commit()
            db.close()
            self.reload_sessions()

    def fix_dropdowns(self):
        db = sqlite3.connect(DB_FILE)
        names = [x[0] for x in db.execute("SELECT name FROM clients WHERE active=1").fetchall()]
        db.close()
        self.client_choice['values'] = names
        self.filter_choice['values'] = ["All Clients"] + names
        self.filter_choice.set("All Clients")

    def make_report_screen(self):
        b_frame = tk.Frame(self.pg3)
        b_frame.pack(pady=10)

        tk.Button(b_frame, text="Generate Data Report", command=self.run_pandas_logic).pack(side="left", padx=10)
        tk.Button(b_frame, text="Export CSV", command=self.save_csv_file).pack(side="left", padx=10)
        tk.Button(b_frame, text="Write Invoice", command=self.build_invoice).pack(side="left", padx=10)

        # Tree for summary
        self.report_tree = ttk.Treeview(self.pg3, columns=("n", "s", "h", "p"), show="headings")
        self.report_tree.heading("n", text="Client")
        self.report_tree.heading("s", text="Total Sessions")
        self.report_tree.heading("h", text="Total Hours")
        self.report_tree.heading("p", text="Total Earnings")
        self.report_tree.pack(fill="both", expand=True, padx=20)

        self.stats_area = tk.Label(self.pg3, text="Summary Stats...", font=("Arial", 10, "bold"))
        self.stats_area.pack(pady=10)

    def run_pandas_logic(self):
        db = sqlite3.connect(DB_FILE)
        query = "SELECT s.*, c.name, c.hourly_rate FROM sessions s JOIN clients c ON s.client_id = c.id"
        self.big_df = pd.read_sql(query, db)
        db.close()

        if self.big_df.empty:
            return

        self.big_df['earnings'] = self.big_df['hours'] * self.big_df['hourly_rate']

      
        summary = self.big_df.groupby('name').agg(
            sessions_count=('id', 'count'),
            total_hours=('hours', 'sum'),
            total_money=('earnings', 'sum')
        ).reset_index()

        
        raw_hours = self.big_df['hours'].to_numpy()
        raw_money = self.big_df['earnings'].to_numpy()
        
        sum_h = np.sum(raw_hours)
        avg_m = np.mean(raw_money)

        # Populate summary tree
        for i in self.report_tree.get_children(): self.report_tree.delete(i)
        for _, row in summary.iterrows():
           
            self.report_tree.insert("", "end", values=(
                row['name'], 
                row['sessions_count'], 
                np.round(row['total_hours'], 2), 
                f"${np.round(row['total_money'], 2)}"
            ))

        self.stats_area.config(text=f"Business Total: {np.round(sum_h, 2)} hrs | Avg Session: ${np.round(avg_m, 2)}")
        self.summary_for_csv = summary

    def save_csv_file(self):
        if hasattr(self, 'summary_for_csv'):
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
            if path:
             
                self.summary_for_csv.to_csv(path, index=False)
                messagebox.showinfo("Saved", "Exported report to CSV.")
        else:
            messagebox.showwarning("Wait", "Run the report first!")

    def build_invoice(self):
        selected = self.report_tree.selection()
        if not selected:
            messagebox.showwarning("Notice", "Select a client in the report table first.")
            return
        
        name = self.report_tree.item(selected[0])['values'][0]
        
        db = sqlite3.connect(DB_FILE)
        client_info = db.execute("SELECT id, hourly_rate FROM clients WHERE name=?", (name,)).fetchone()
        sess_data = db.execute("SELECT date, hours, description FROM sessions WHERE client_id=?", (client_info[0],)).fetchall()
        db.close()

        # Build the text string
        txt = f"FREELANCE INVOICE\n{'='*20}\n"
        txt += f"TO: {name}\nDATE: {datetime.now().strftime('%Y-%m-%d')}\n"
        txt += f"RATE: ${client_info[1]}/hr\n\n"
        txt += f"{'Date':<15} {'Hours':<10} {'Details'}\n"
        txt += f"{'-'*45}\n"
        
        total_hrs = 0
        for s in sess_data:
            txt += f"{s[0]:<15} {s[1]:<10} {s[2]}\n"
            total_hrs += s[1]
        
        txt += f"{'-'*45}\n"
        txt += f"TOTAL HOURS: {total_hrs:.2f}\n"
        txt += f"AMOUNT DUE:  ${(total_hrs * client_info[1]):.2f}\n"

       
        target_path = filedialog.asksaveasfilename(defaultextension='.txt', filetypes=[('Text files', '*.txt')])
        if not target_path:
            return 
            
        with open(target_path, 'w') as f:
            f.write(txt)
        messagebox.showinfo("Success", f"Invoice saved to {target_path}")

if __name__ == "__main__":
    main_root = tk.Tk()
    app_instance = MyFreelanceApp(main_root)
    main_root.mainloop()