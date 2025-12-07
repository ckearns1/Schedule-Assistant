import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd

def import_csv():
    file_path = filedialog.askopenfilename(
        title="Select CSV File",
        filetypes=[("CSV files", "*.csv")]
    )
    if not file_path:
        return None
    try:
        df = pd.read_csv(file_path, index_col=0)
        print("\n=== Preview of Imported CSV ===")
        print(df.head())
        print("\nColumns (days of week):", df.columns.tolist())
        print("Index (time slots):", df.index.tolist()[:5], "...")
        messagebox.showinfo("Success", f"Imported {file_path}")
        return df
    except Exception as e:
        messagebox.showerror("Error", f"Failed to import CSV:\n{e}")
        return None

def main():
    root = tk.Tk()
    root.withdraw()
    df = import_csv()
    if df is not None:
        print("\nDataFrame shape:", df.shape)

if __name__ == "__main__":
    main()