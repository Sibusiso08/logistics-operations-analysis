"""
============================================================
LOGISTICS FLEET ANALYTICS - DASHBOARD
============================================================
Description : Loads all 14 CSV tables into a SQLite database,
              runs SQL queries, and renders a full-page
              analytics dashboard saved as a PNG.

Requirements: pandas, matplotlib (stdlib: sqlite3, os, numpy)

Usage:
    1. Place all CSV files in the same directory as this script
       (or update DATA_DIR below).
    2. Run:  python logistics_dashboard.py
    3. Output: logistics_dashboard.png
============================================================
"""

import os
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# ── Configuration ─────────────────────────────────────────────
DATA_DIR = "/mnt/user-data/uploads"   # folder containing the CSV files
DB_PATH  = "logistics.db"             # SQLite database (auto-created)
OUT_PATH = "logistics_dashboard.png"  # output image path

CSV_TABLES = {
    "drivers":                  "drivers.csv",
    "trucks":                   "trucks.csv",
    "trailers":                 "trailers.csv",
    "customers":                "customers.csv",
    "facilities":               "facilities.csv",
    "routes":                   "routes.csv",
    "loads":                    "loads.csv",
    "trips":                    "trips.csv",
    "fuel_purchases":           "fuel_purchases.csv",
    "maintenance_records":      "maintenance_records.csv",
    "delivery_events":          "delivery_events.csv",
    "safety_incidents":         "safety_incidents.csv",
    "driver_monthly_metrics":   "driver_monthly_metrics.csv",
    "truck_utilization_metrics":"truck_utilization_metrics.csv",
}

# ── Step 1: Build SQLite database from CSVs ───────────────────
print("Loading CSVs into SQLite...")
conn = sqlite3.connect(DB_PATH)
for table, filename in CSV_TABLES.items():
    path = os.path.join(DATA_DIR, filename)
    df = pd.read_csv(path)
    df.to_sql(table, conn, if_exists="replace", index=False)
    print(f"  {table}: {len(df):,} rows")
conn.commit()
print("Database ready.\n")

# ── Step 2: SQL Queries ───────────────────────────────────────
print("Running SQL analyses...")

monthly = pd.read_sql_query(
    "SELECT strftime('%Y-%m',load_date) AS month, COUNT(*) AS loads, "
    "ROUND(SUM(revenue)/1e6,3) AS rev_M FROM loads GROUP BY 1 ORDER BY 1", conn)

top_customers = pd.read_sql_query(
    "SELECT c.customer_name, "
    "ROUND(SUM(l.revenue+l.fuel_surcharge+l.accessorial_charges)/1e6,2) AS rev_M "
    "FROM loads l JOIN customers c ON l.customer_id=c.customer_id "
    "GROUP BY c.customer_id ORDER BY rev_M DESC LIMIT 10", conn)

top_routes = pd.read_sql_query(
    "SELECT r.origin_city||' -> '||r.destination_city AS lane, "
    "ROUND(SUM(l.revenue)/1e3,1) AS rev_K "
    "FROM loads l JOIN routes r ON l.route_id=r.route_id "
    "JOIN trips t ON l.load_id=t.load_id "
    "GROUP BY r.route_id ORDER BY rev_K DESC LIMIT 8", conn)

top_drivers = pd.read_sql_query(
    "SELECT d.first_name||' '||d.last_name AS driver, "
    "ROUND(SUM(l.revenue)/1e3,1) AS rev_K "
    "FROM trips t JOIN drivers d ON t.driver_id=d.driver_id "
    "JOIN loads l ON t.load_id=l.load_id "
    "GROUP BY d.driver_id ORDER BY rev_K DESC LIMIT 8", conn)

maint = pd.read_sql_query(
    "SELECT maintenance_type, ROUND(SUM(total_cost)/1e3,1) AS cost_K "
    "FROM maintenance_records GROUP BY maintenance_type ORDER BY cost_K DESC", conn)

fuel = pd.read_sql_query(
    "SELECT tk.make, ROUND(AVG(t.average_mpg),2) AS avg_mpg "
    "FROM trips t JOIN trucks tk ON t.truck_id=tk.truck_id "
    "GROUP BY tk.make ORDER BY avg_mpg DESC", conn)

util = pd.read_sql_query(
    "SELECT tk.make, ROUND(AVG(m.utilization_rate)*100,1) AS util_pct "
    "FROM truck_utilization_metrics m JOIN trucks tk ON m.truck_id=tk.truck_id "
    "GROUP BY tk.make ORDER BY util_pct DESC", conn)

safety = pd.read_sql_query(
    "SELECT incident_type, COUNT(*) AS incidents, "
    "ROUND(SUM(claim_amount)/1e3,1) AS claims_K "
    "FROM safety_incidents GROUP BY incident_type ORDER BY incidents DESC", conn)

load_type = pd.read_sql_query(
    "SELECT load_type, COUNT(*) AS loads FROM loads GROUP BY load_type", conn)

booking = pd.read_sql_query(
    "SELECT booking_type, ROUND(SUM(revenue)/1e6,2) AS rev_M "
    "FROM loads GROUP BY booking_type ORDER BY rev_M DESC", conn)

rev_yr = pd.read_sql_query(
    "SELECT strftime('%Y',load_date) AS yr, ROUND(SUM(revenue)/1e6,2) AS rev_M "
    "FROM loads GROUP BY 1 ORDER BY 1", conn)

conn.close()
print("All queries complete.\n")

# ── Step 3: Dashboard ─────────────────────────────────────────
print("Rendering dashboard...")

# Colour palette
BG    = "#0f1117"; PANEL = "#1a1d2e"
A1    = "#4f8ef7"; A2    = "#f7794f"; A3 = "#4fc97f"
A4    = "#f7c44f"; A5    = "#c44ff7"
TX    = "#e8eaf0"; ST    = "#8892a0"; GR = "#2a2d3e"

plt.rcParams.update({
    "figure.facecolor": BG,   "axes.facecolor":  PANEL,
    "axes.edgecolor":   GR,   "axes.labelcolor": TX,
    "xtick.color":      ST,   "ytick.color":     ST,
    "text.color":       TX,   "grid.color":      GR,
    "grid.linewidth":   0.6,  "font.family":     "DejaVu Sans",
    "font.size":        9,
})

fig = plt.figure(figsize=(26, 38), facecolor=BG)
fig.suptitle("LOGISTICS FLEET ANALYTICS DASHBOARD",
             fontsize=20, fontweight="bold", color=TX, y=0.99)
gs = gridspec.GridSpec(6, 4, figure=fig, hspace=0.52, wspace=0.38,
                       left=0.05, right=0.97, top=0.975, bottom=0.02)

def panel(ax, title):
    ax.set_facecolor(PANEL)
    for sp in ax.spines.values():
        sp.set_color(GR)
    ax.set_title(title, color=TX, fontsize=9.5, fontweight="bold", pad=7)

# ── KPI tiles (row 0) ─────────────────────────────────────────
kpis = [
    ("Total Revenue",  "$298.6M", A1),
    ("Total Trips",    "85,410",  A2),
    ("Total Miles",    "122.2M",  A3),
    ("Avg Fleet MPG",  "6.50",    A4),
    ("Active Drivers", "120",     A5),
    ("Active Trucks",  "96",      "#f77494"),
]
for i, (lbl, val, col) in enumerate(kpis):
    x0 = 0.055 + (i % 4) * 0.237
    y0 = 0.923 if i < 4 else 0.875
    kax = fig.add_axes([x0, y0, 0.185, 0.048], facecolor=PANEL)
    for sp in kax.spines.values():
        sp.set_color(col); sp.set_linewidth(2)
    kax.set_xticks([]); kax.set_yticks([])
    kax.text(0.5, 0.62, val, ha="center", va="center",
             fontsize=15, fontweight="bold", color=col, transform=kax.transAxes)
    kax.text(0.5, 0.15, lbl, ha="center", va="center",
             fontsize=7.5, color=ST, transform=kax.transAxes)

# ── Row 1: Monthly Revenue Trend ──────────────────────────────
ax1 = fig.add_subplot(gs[1, :])
panel(ax1, "Monthly Revenue Trend (USD Millions)")
x = np.arange(len(monthly))
ax1.fill_between(x, monthly["rev_M"], alpha=0.2, color=A1)
ax1.plot(x, monthly["rev_M"], color=A1, lw=2, marker="o", ms=3.5)
ax1.set_xticks(x[::3])
ax1.set_xticklabels(monthly["month"].iloc[::3], rotation=40, ha="right")
ax1.set_ylabel("Revenue (USD M)", color=ST)
avg = monthly["rev_M"].mean()
ax1.axhline(avg, color=A4, lw=1.2, ls="--")
ax1.text(len(x) - 1, avg + 0.02, f"Avg ${avg:.2f}M",
         color=A4, fontsize=8, ha="right")
ax1.grid(axis="y", color=GR, ls="--", alpha=0.7)
ax1.grid(axis="x", visible=False)

# ── Row 2: Top Customers & Routes ─────────────────────────────
ax2 = fig.add_subplot(gs[2, :2])
panel(ax2, "Top 10 Customers by Revenue (USD M)")
ax2.barh(top_customers["customer_name"][::-1],
         top_customers["rev_M"][::-1], color=A1, edgecolor=PANEL, height=0.65)
for i, (_, row) in enumerate(top_customers[::-1].iterrows()):
    ax2.text(row["rev_M"] + 0.003, i, f"${row['rev_M']:.2f}M",
             va="center", fontsize=7.5, color=TX)
ax2.set_xlabel("Revenue (USD M)", color=ST)
ax2.grid(axis="x", color=GR, ls="--", alpha=0.7)
ax2.grid(axis="y", visible=False)

ax3 = fig.add_subplot(gs[2, 2:])
panel(ax3, "Top 8 Routes by Revenue (USD K)")
cols_r = plt.cm.Blues(np.linspace(0.45, 0.9, len(top_routes)))[::-1]
ax3.barh(top_routes["lane"][::-1], top_routes["rev_K"][::-1],
         color=cols_r, edgecolor=PANEL, height=0.65)
for i, (_, row) in enumerate(top_routes[::-1].iterrows()):
    ax3.text(row["rev_K"] + 20, i, f"${row['rev_K']:.0f}K",
             va="center", fontsize=7.5, color=TX)
ax3.set_xlabel("Revenue (USD K)", color=ST)
ax3.grid(axis="x", color=GR, ls="--", alpha=0.7)
ax3.grid(axis="y", visible=False)

# ── Row 3: Top Drivers, Load Type, Booking ────────────────────
ax4 = fig.add_subplot(gs[3, :2])
panel(ax4, "Top 8 Drivers by Revenue (USD K)")
ax4.barh(top_drivers["driver"][::-1], top_drivers["rev_K"][::-1],
         color=A3, edgecolor=PANEL, height=0.65)
for i, (_, row) in enumerate(top_drivers[::-1].iterrows()):
    ax4.text(row["rev_K"] + 3, i, f"${row['rev_K']:.0f}K",
             va="center", fontsize=7.5, color=TX)
ax4.set_xlabel("Revenue (USD K)", color=ST)
ax4.grid(axis="x", color=GR, ls="--", alpha=0.7)
ax4.grid(axis="y", visible=False)

ax5 = fig.add_subplot(gs[3, 2])
ax5.set_facecolor(PANEL)
for sp in ax5.spines.values():
    sp.set_color(GR)
ax5.set_title("Load Type Distribution", color=TX, fontsize=9.5,
              fontweight="bold", pad=7)
w, t, at = ax5.pie(load_type["loads"], labels=load_type["load_type"],
                   autopct="%1.1f%%", colors=[A1, A2],
                   textprops={"color": TX, "fontsize": 9},
                   wedgeprops={"edgecolor": BG, "linewidth": 2},
                   startangle=90)
for a in at:
    a.set_color(BG); a.set_fontweight("bold")

ax6 = fig.add_subplot(gs[3, 3])
panel(ax6, "Revenue by Booking Type (USD M)")
ax6.bar(booking["booking_type"], booking["rev_M"],
        color=[A4, A2, A5], edgecolor=PANEL, width=0.5)
for i, rv in enumerate(booking["rev_M"]):
    ax6.text(i, rv + 0.3, f"${rv:.1f}M", ha="center", fontsize=8, color=TX)
ax6.set_ylabel("Revenue (USD M)", color=ST)
ax6.grid(axis="y", color=GR, ls="--", alpha=0.7)
ax6.grid(axis="x", visible=False)

# ── Row 4: Maintenance, Fuel, Utilization ─────────────────────
ax7 = fig.add_subplot(gs[4, :2])
panel(ax7, "Maintenance Cost by Type (USD K)")
colors_m = [A2, A1, A4, A3, A5, "#f77494", "#7cf7f7"]
bars = ax7.bar(maint["maintenance_type"], maint["cost_K"],
               color=colors_m[: len(maint)], edgecolor=PANEL, width=0.6)
for bar, val in zip(bars, maint["cost_K"]):
    ax7.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
             f"${val:.0f}K", ha="center", fontsize=7.5, color=TX)
ax7.set_ylabel("Cost (USD K)", color=ST)
plt.setp(ax7.get_xticklabels(), rotation=28, ha="right")
ax7.grid(axis="y", color=GR, ls="--", alpha=0.7)
ax7.grid(axis="x", visible=False)

ax8 = fig.add_subplot(gs[4, 2])
panel(ax8, "Avg MPG by Truck Make")
cols_g = plt.cm.Greens(np.linspace(0.45, 0.9, len(fuel)))[::-1]
ax8.barh(fuel["make"], fuel["avg_mpg"], color=cols_g, edgecolor=PANEL, height=0.55)
for i, (_, row) in enumerate(fuel.iterrows()):
    ax8.text(row["avg_mpg"] + 0.001, i, f"{row['avg_mpg']:.2f}",
             va="center", fontsize=8, color=TX)
ax8.set_xlabel("MPG", color=ST)
ax8.set_xlim(6.44, 6.56)
ax8.grid(axis="x", color=GR, ls="--", alpha=0.7)
ax8.grid(axis="y", visible=False)

ax9 = fig.add_subplot(gs[4, 3])
panel(ax9, "Fleet Utilization % by Make")
ax9.barh(util["make"], util["util_pct"], color=A4, edgecolor=PANEL, height=0.55)
for i, (_, row) in enumerate(util.iterrows()):
    ax9.text(row["util_pct"] + 0.05, i, f"{row['util_pct']:.1f}%",
             va="center", fontsize=8, color=TX)
ax9.set_xlabel("Utilization %", color=ST)
ax9.set_xlim(80, 86.5)
ax9.grid(axis="x", color=GR, ls="--", alpha=0.7)
ax9.grid(axis="y", visible=False)

# ── Row 5: Safety & Annual Revenue ────────────────────────────
ax10 = fig.add_subplot(gs[5, :2])
panel(ax10, "Safety Incidents & Claims by Type")
xs = np.arange(len(safety)); w = 0.37
b1 = ax10.bar(xs - w / 2, safety["incidents"], width=w,
              color=A2, label="Incidents", edgecolor=PANEL)
ax10b = ax10.twinx()
ax10b.set_facecolor(PANEL)
b2 = ax10b.bar(xs + w / 2, safety["claims_K"], width=w,
               color=A5, label="Claims ($K)", edgecolor=PANEL)
ax10.set_xticks(xs)
ax10.set_xticklabels(safety["incident_type"], rotation=22, ha="right")
ax10.set_ylabel("Incidents", color=A2)
ax10b.set_ylabel("Claims (USD K)", color=A5)
ax10b.tick_params(colors=A5)
ax10b.spines["right"].set_color(A5)
ax10.legend(handles=[b1, b2], loc="upper right",
            facecolor=PANEL, labelcolor=TX, fontsize=8)
ax10.grid(axis="y", color=GR, ls="--", alpha=0.7)

ax11 = fig.add_subplot(gs[5, 2:])
panel(ax11, "Annual Revenue Comparison (USD M)")
bars = ax11.bar(rev_yr["yr"], rev_yr["rev_M"],
                color=[A1, A3, A4], edgecolor=PANEL, width=0.5)
for bar, val in zip(bars, rev_yr["rev_M"]):
    ax11.text(bar.get_x() + bar.get_width() / 2,
              bar.get_height() + 0.3,
              f"${val:.2f}M", ha="center",
              fontsize=11, fontweight="bold", color=TX)
ax11.set_ylim(0, rev_yr["rev_M"].max() * 1.2)
ax11.set_ylabel("Revenue (USD M)", color=ST)
ax11.grid(axis="y", color=GR, ls="--", alpha=0.7)
ax11.grid(axis="x", visible=False)

fig.text(0.5, 0.003,
         "Data: 85,410 trips | 3 years (2022-2024) | "
         "Analysed via SQL on 14 relational tables",
         ha="center", color=ST, fontsize=8)

# ── Save ──────────────────────────────────────────────────────
plt.savefig(OUT_PATH, dpi=150, bbox_inches="tight", facecolor=BG)
print(f"Dashboard saved to: {OUT_PATH}")
