import tkinter as tk
import customtkinter as ctk

app = ctk.CTk()
app.geometry("800x400")

th = ctk.CTkFrame(app, fg_color="red")
th.pack(fill="x", padx=12, pady=(12, 4))
for i, h in enumerate(["Process", "PID", "CPU%", "Mem%", "RSS", "Threads"]):
    th.columnconfigure(i, weight=1 if i > 0 else 3, uniform="col")
    ctk.CTkLabel(th, text=h, anchor="w" if i==0 else "center").grid(row=0, column=i, sticky="nsew")

for i in range(3):
    row = ctk.CTkFrame(app, fg_color="blue")
    row.pack(fill="x", padx=12, pady=1)
    vals = ["A very long process name here", "1234", "100.0", "90.0", "12MB", "120"]
    for j, val in enumerate(vals):
        row.columnconfigure(j, weight=1 if j > 0 else 3, uniform="col")
        ctk.CTkLabel(row, text=val, anchor="w" if j==0 else "center").grid(row=0, column=j, sticky="nsew")

app.update()
print("Header columns:", [th.grid_bbox(i, 0) for i in range(6)])
print("Row columns:", [row.grid_bbox(i, 0) for i in range(6)])
