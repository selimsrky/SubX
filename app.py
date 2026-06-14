import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import database as db
import yfinance as yf
import threading
import collections
import csv
import os
import time

class SubXApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SubX - Login")
        self.root.geometry("400x300")
        self.root.configure(padx=20, pady=20)

        db.init_db()
        
        # User State
        self.user_id = None
        self.username = ""

        # Market Data Maps
        self.fx_map = {"USD/TRY": "USDTRY=X", "EUR/TRY": "EURTRY=X", "GBP/TRY": "GBPTRY=X"}
        self.bist_map = {"THYAO": "THYAO.IS", "KCHOL": "KCHOL.IS", "TUPRS": "TUPRS.IS", "ASELS": "ASELS.IS", "GARAN": "GARAN.IS"}
        self.us_map = {"AAPL": "AAPL", "NVDA": "NVDA", "TSLA": "TSLA", "MSFT": "MSFT", "BTC-USD": "BTC-USD"}
        self.all_symbols = list(self.fx_map.values()) + list(self.bist_map.values()) + list(self.us_map.values())
        
        # Memory for Live Prices and Charts
        self.live_prices = {sym: 0.0 for sym in self.all_symbols}
        self.prev_prices = {sym: 0.0 for sym in self.all_symbols}
        self.histories = {sym: collections.deque(maxlen=60) for sym in self.all_symbols}
        
        # UI State Variables
        self.current_fx_pair = "USD/TRY"
        self.current_fx_period = "Live Stream"
        self.current_stock = "NVDA"
        self.current_stock_period = "Live Stream"

        self.is_running = True
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Start with Login Screen
        self.build_login_screen()

    def on_closing(self):
        self.is_running = False
        plt.close('all')
        self.root.destroy()

    # ==========================================
    # LOGIN & AUTHENTICATION SYSTEM
    # ==========================================
    def build_login_screen(self):
        self.login_frame = ttk.Frame(self.root)
        self.login_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(self.login_frame, text="SubX Financial Terminal", font=("Arial", 16, "bold")).pack(pady=20)

        form_frame = ttk.Frame(self.login_frame)
        form_frame.pack(pady=10)

        ttk.Label(form_frame, text="Username:").grid(row=0, column=0, pady=5, sticky=tk.E)
        self.entry_user = ttk.Entry(form_frame, width=20)
        self.entry_user.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(form_frame, text="Password:").grid(row=1, column=0, pady=5, sticky=tk.E)
        self.entry_pass = ttk.Entry(form_frame, width=20, show="*")
        self.entry_pass.grid(row=1, column=1, pady=5, padx=5)

        btn_frame = ttk.Frame(self.login_frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Login", command=self.login_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Sign Up", command=self.register_user).pack(side=tk.LEFT, padx=5)

    def login_user(self):
        user = self.entry_user.get().strip()
        pwd = self.entry_pass.get().strip()
        user_id = db.authenticate_user(user, pwd)
        
        if user_id:
            self.user_id = user_id
            self.username = user
            self.login_frame.destroy()
            self.launch_main_app()
        else:
            messagebox.showerror("Error", "Invalid username or password.")

    def register_user(self):
        user = self.entry_user.get().strip()
        pwd = self.entry_pass.get().strip()
        if not user or not pwd:
            messagebox.showwarning("Warning", "Fields cannot be empty.")
            return
            
        if db.create_user(user, pwd):
            messagebox.showinfo("Success", f"User '{user}' created! You start with $10,000. Please login.")
        else:
            messagebox.showerror("Error", "Username already exists!")

    # ==========================================
    # LAUNCH MAIN APP & THREADS
    # ==========================================
    def launch_main_app(self):
        self.root.title(f"SubX Terminal - Logged in as: {self.username}")
        self.root.geometry("1250x850")
        
        self.setup_ui()
        self.preload_recent_history()
        self.start_background_live_feed()

    def preload_recent_history(self):
        """Preloads the last 60 data points so live charts are not empty at startup."""
        def task():
            for sym in self.all_symbols:
                try:
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(period="1d", interval="5m")
                    if not hist.empty:
                        prices = hist['Close'].tolist()[-60:]
                        times = [d.strftime('%H:%M') for d in hist.index[-60:]]
                        for t, p in zip(times, prices):
                            self.histories[sym].append((t, p))
                        self.live_prices[sym] = prices[-1]
                except:
                    pass
        threading.Thread(target=task, daemon=True).start()

    def start_background_live_feed(self):
        """Fetches live prices from Yahoo Finance every 10 seconds."""
        def fetch_loop():
            while self.is_running:
                try:
                    now_str = time.strftime('%H:%M:%S')
                    
                    for sym in self.all_symbols:
                        try:
                            ticker = yf.Ticker(sym)
                            try:
                                current_price = ticker.fast_info['lastPrice']
                            except:
                                hist = ticker.history(period="1d", interval="1m")
                                current_price = float(hist['Close'].iloc[-1]) if not hist.empty else 0.0
                            
                            if current_price > 0:
                                self.prev_prices[sym] = self.live_prices[sym]
                                self.live_prices[sym] = current_price
                                self.histories[sym].append((now_str, current_price))
                        except:
                            pass
                            
                    self.root.after(0, self.update_ui_with_live_data)
                except Exception as e:
                    print("Data Fetch Error:", e)
                
                for _ in range(10):
                    if not self.is_running: break
                    time.sleep(1)

        threading.Thread(target=fetch_loop, daemon=True).start()

    def update_ui_with_live_data(self):
        self.refresh_sub_data()
        self.refresh_portfolio_data() 

        # Update FX Table & Live Chart
        for display_name, yf_sym in self.fx_map.items():
            if self.tree_fx.exists(display_name):
                price = self.live_prices[yf_sym]
                trend = "▲" if price >= self.prev_prices[yf_sym] else "▼"
                self.tree_fx.item(display_name, values=(display_name, f"{price:.4f} ₺", trend))
        
        if self.current_fx_period == "Live Stream":
            self.draw_fx_live_chart()

        # Update Stocks Table & Live Chart
        for display_name, yf_sym in self.bist_map.items():
            if self.tree_bist.exists(display_name):
                price = self.live_prices[yf_sym]
                trend = "▲" if price >= self.prev_prices[yf_sym] else "▼"
                self.tree_bist.item(display_name, values=(display_name, f"{price:.2f} ₺", trend))

        for display_name, yf_sym in self.us_map.items():
            if self.tree_us.exists(display_name):
                price = self.live_prices[yf_sym]
                trend = "▲" if price >= self.prev_prices[yf_sym] else "▼"
                self.tree_us.item(display_name, values=(display_name, f"${price:.2f}", trend))
        
        if self.current_stock_period == "Live Stream":
            self.draw_stock_live_chart()

    # ==========================================
    # UI SETUP & TABS
    # ==========================================
    def setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_subs = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_subs, text="Subscription Manager")

        self.tab_market = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_market, text="Live FX Charts")
        
        self.tab_stocks = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_stocks, text="Global Stock Market")
        
        self.tab_trading = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_trading, text="Trading Desk & Portfolio")

        self.build_subscription_tab()
        self.build_market_tab()
        self.build_stocks_tab()
        self.build_trading_tab()

    # --- TAB 1: SUBSCRIPTIONS ---
    def build_subscription_tab(self):
        left_frame = ttk.Frame(self.tab_subs)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        form_frame = ttk.LabelFrame(left_frame, text="Add New Subscription", padding=10)
        form_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(form_frame, text="Platform Name:").grid(row=0, column=0, pady=5)
        self.entry_name = ttk.Entry(form_frame, width=20); self.entry_name.grid(row=0, column=1)
        ttk.Label(form_frame, text="Amount:").grid(row=1, column=0, pady=5)
        self.entry_amount = ttk.Entry(form_frame, width=20); self.entry_amount.grid(row=1, column=1)
        ttk.Label(form_frame, text="Currency:").grid(row=2, column=0, pady=5)
        self.combo_currency = ttk.Combobox(form_frame, values=["TRY", "USD"], state="readonly")
        self.combo_currency.current(0); self.combo_currency.grid(row=2, column=1)
        ttk.Label(form_frame, text="Renewal Day (1-31):").grid(row=3, column=0, pady=5)
        self.entry_day = ttk.Entry(form_frame, width=20); self.entry_day.grid(row=3, column=1)
        ttk.Button(form_frame, text="Add", command=self.add_subscription).grid(row=4, column=0, columnspan=2, pady=10)
        
        list_frame = ttk.LabelFrame(left_frame, text="Current Subscriptions", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        self.tree_subs = ttk.Treeview(list_frame, columns=("id", "name", "amount", "currency", "day", "try_equiv"), show="headings", height=7)
        for c, txt in zip(self.tree_subs["columns"], ["ID","Platform","Amount","Currency","Day","TRY Equiv."]):
            self.tree_subs.heading(c, text=txt)
        self.tree_subs.pack(fill=tk.BOTH, expand=True)
        ttk.Button(list_frame, text="Delete Selected", command=self.delete_subscription).pack(fill=tk.X)

        right_frame = ttk.Frame(self.tab_subs)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        info_frame = ttk.LabelFrame(right_frame, text="Financial Summary", padding=10)
        info_frame.pack(fill=tk.X)
        self.lbl_monthly = ttk.Label(info_frame, text="Monthly Total: 0.00 TRY", font=("Arial", 12, "bold"))
        self.lbl_monthly.pack(anchor=tk.W)
        self.lbl_yearly = ttk.Label(info_frame, text="Yearly Total: 0.00 TRY", font=("Arial", 12, "bold"))
        self.lbl_yearly.pack(anchor=tk.W)

    # --- TAB 2: FX MARKET ---
    def build_market_tab(self):
        top_frame = ttk.LabelFrame(self.tab_market, text="Live FX Rates Overview", padding=10)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        self.tree_fx = ttk.Treeview(top_frame, columns=("pair", "price", "status"), show="headings", height=3)
        self.tree_fx.heading("pair", text="Currency Pair"); self.tree_fx.heading("price", text="Price"); self.tree_fx.heading("status", text="Trend")
        self.tree_fx.pack(fill=tk.X, expand=True)
        for pair in self.fx_map.keys(): self.tree_fx.insert("", tk.END, iid=pair, values=(pair, "Loading...", "-"))

        control_frame = ttk.Frame(self.tab_market)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(control_frame, text="Pair:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.combo_fx_pair = ttk.Combobox(control_frame, values=list(self.fx_map.keys()), state="readonly", width=12)
        self.combo_fx_pair.current(0)
        self.combo_fx_pair.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(control_frame, text="Timeframe:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.combo_fx_period = ttk.Combobox(control_frame, values=["Live Stream", "Past 1 Day", "Past 1 Month", "Past 1 Year"], state="readonly", width=15)
        self.combo_fx_period.current(0)
        self.combo_fx_period.pack(side=tk.LEFT)
        
        ttk.Button(control_frame, text="Load Chart", command=self.on_fx_chart_load).pack(side=tk.LEFT, padx=15)

        bottom_frame = ttk.LabelFrame(self.tab_market, text="Interactive FX Chart", padding=10)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.fig_fx, self.ax_fx = plt.subplots(figsize=(8, 4), dpi=100)
        self.canvas_fx = FigureCanvasTkAgg(self.fig_fx, master=bottom_frame)
        self.canvas_fx.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def on_fx_chart_load(self):
        self.current_fx_pair = self.combo_fx_pair.get()
        self.current_fx_period = self.combo_fx_period.get()
        
        if self.current_fx_period == "Live Stream":
            self.draw_fx_live_chart()
        else:
            yf_sym = self.fx_map[self.current_fx_pair]
            self.fetch_and_plot_history(yf_sym, self.current_fx_period, self.ax_fx, self.canvas_fx, self.current_fx_pair)

    def draw_fx_live_chart(self):
        yf_sym = self.fx_map.get(self.current_fx_pair)
        if not yf_sym: return
        data = list(self.histories[yf_sym])
        if not data: return

        times = [item[0] for item in data]
        prices = [item[1] for item in data]

        self.ax_fx.clear()
        self.ax_fx.plot(times, prices, color="#2196F3", marker='o', markersize=4, linestyle='-')
        self.ax_fx.set_title(f"Real-Time Live Stream: {self.current_fx_pair}")
        self.ax_fx.set_ylabel("Price")
        
        min_p, max_p = min(prices), max(prices)
        padding = (max_p - min_p) * 0.1 if max_p != min_p else 0.5
        self.ax_fx.set_ylim(min_p - padding, max_p + padding)
        
        self.ax_fx.grid(True, linestyle='--', alpha=0.5)
        
        step = max(1, len(times) // 8)
        self.ax_fx.set_xticks(times[::step])
        self.ax_fx.tick_params(axis='x', rotation=45, labelsize=8)
        
        self.fig_fx.tight_layout()
        self.canvas_fx.draw()

    # --- TAB 3: STOCKS MARKET ---
    def build_stocks_tab(self):
        top_frame = ttk.Frame(self.tab_stocks)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        bist_frame = ttk.LabelFrame(top_frame, text="Turkish Market (BIST 30)", padding=10)
        bist_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.tree_bist = ttk.Treeview(bist_frame, columns=("ticker", "price", "status"), show="headings", height=5)
        self.tree_bist.heading("ticker", text="Ticker"); self.tree_bist.heading("price", text="Price (TRY)"); self.tree_bist.heading("status", text="Trend")
        self.tree_bist.pack(fill=tk.BOTH, expand=True)
        for ticker in self.bist_map.keys(): self.tree_bist.insert("", tk.END, iid=ticker, values=(ticker, "Loading...", "-"))

        us_frame = ttk.LabelFrame(top_frame, text="Global Markets (US & Crypto)", padding=10)
        us_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.tree_us = ttk.Treeview(us_frame, columns=("ticker", "price", "status"), show="headings", height=5)
        self.tree_us.heading("ticker", text="Ticker"); self.tree_us.heading("price", text="Price ($)"); self.tree_us.heading("status", text="Trend")
        self.tree_us.pack(fill=tk.BOTH, expand=True)
        for ticker in self.us_map.keys(): self.tree_us.insert("", tk.END, iid=ticker, values=(ticker, "Loading...", "-"))

        control_frame = ttk.Frame(self.tab_stocks)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(control_frame, text="Stock:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        all_stocks = list(self.bist_map.keys()) + list(self.us_map.keys())
        self.combo_stock = ttk.Combobox(control_frame, values=all_stocks, state="readonly", width=12)
        self.combo_stock.set("NVDA")
        self.combo_stock.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(control_frame, text="Timeframe:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.combo_stock_period = ttk.Combobox(control_frame, values=["Live Stream", "Past 1 Day", "Past 1 Month", "Past 1 Year"], state="readonly", width=15)
        self.combo_stock_period.current(0)
        self.combo_stock_period.pack(side=tk.LEFT)
        
        ttk.Button(control_frame, text="Load Chart", command=self.on_stock_chart_load).pack(side=tk.LEFT, padx=15)

        bottom_frame = ttk.LabelFrame(self.tab_stocks, text="Interactive Stock Chart", padding=10)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.fig_stock, self.ax_stock = plt.subplots(figsize=(8, 3), dpi=100)
        self.canvas_stock = FigureCanvasTkAgg(self.fig_stock, master=bottom_frame)
        self.canvas_stock.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def on_stock_chart_load(self):
        self.current_stock = self.combo_stock.get()
        self.current_stock_period = self.combo_stock_period.get()
        
        if self.current_stock_period == "Live Stream":
            self.draw_stock_live_chart()
        else:
            yf_sym = self.bist_map.get(self.current_stock) or self.us_map.get(self.current_stock)
            self.fetch_and_plot_history(yf_sym, self.current_stock_period, self.ax_stock, self.canvas_stock, self.current_stock)

    def draw_stock_live_chart(self):
        yf_sym = self.bist_map.get(self.current_stock) or self.us_map.get(self.current_stock)
        if not yf_sym: return
        data = list(self.histories[yf_sym])
        if not data: return

        times = [item[0] for item in data]
        prices = [item[1] for item in data]

        self.ax_stock.clear()
        color = "#E91E63" if yf_sym in self.bist_map.values() else "#4CAF50"
        self.ax_stock.plot(times, prices, color=color, marker='s', markersize=3, linestyle='-')
        self.ax_stock.set_title(f"Real-Time Live Stream: {self.current_stock}")
        self.ax_stock.set_ylabel("Price")
        
        min_p, max_p = min(prices), max(prices)
        padding = (max_p - min_p) * 0.1 if max_p != min_p else 1.0
        self.ax_stock.set_ylim(min_p - padding, max_p + padding)
        
        self.ax_stock.grid(True, linestyle='--', alpha=0.5)
        
        step = max(1, len(times) // 8)
        self.ax_stock.set_xticks(times[::step])
        self.ax_stock.tick_params(axis='x', rotation=45, labelsize=8)
        
        self.fig_stock.tight_layout()
        self.canvas_stock.draw()

    # ==========================================
    # HISTORICAL DATA DOWNLOADER & PLOTTER
    # ==========================================
    def fetch_and_plot_history(self, yf_symbol, period_name, ax, canvas, title):
        """Downloads historical data from Yahoo Finance in a separate thread."""
        ax.clear()
        ax.text(0.5, 0.5, "Downloading Internet Data...", horizontalalignment='center', verticalalignment='center', fontsize=12)
        canvas.draw()
        
        def task():
            try:
                if period_name == "Past 1 Day":
                    period, interval = "1d", "5m"
                elif period_name == "Past 1 Month":
                    period, interval = "1mo", "1d"
                else: 
                    period, interval = "1y", "1wk"

                hist = yf.Ticker(yf_symbol).history(period=period, interval=interval)
                
                if hist.empty:
                    self.root.after(0, lambda: self._show_error_chart(ax, canvas, "Market Closed or No Data Available."))
                    return

                prices = hist['Close'].tolist()
                
                if interval == "5m":
                    dates = [d.strftime('%H:%M') for d in hist.index]
                else:
                    dates = [d.strftime('%Y-%m-%d') for d in hist.index]

                self.root.after(0, lambda: self._render_history_chart(ax, canvas, dates, prices, title, period_name))
            except Exception as e:
                self.root.after(0, lambda: self._show_error_chart(ax, canvas, f"Network Error: {e}"))

        threading.Thread(target=task, daemon=True).start()

    def _render_history_chart(self, ax, canvas, dates, prices, title, period_name):
        ax.clear()
        step = max(1, len(dates) // 10) 
        
        color = "#2196F3" if "TRY" in title else "#E91E63"
        ax.plot(dates, prices, color=color, linewidth=2)
        ax.set_title(f"Historical Data: {title} ({period_name})")
        ax.set_ylabel("Price")
        ax.grid(True, linestyle='--', alpha=0.5)
        
        ax.set_xticks(dates[::step])
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        
        ax.figure.tight_layout()
        canvas.draw()

    def _show_error_chart(self, ax, canvas, msg):
        ax.clear()
        ax.text(0.5, 0.5, msg, horizontalalignment='center', verticalalignment='center', color='red', fontsize=12)
        canvas.draw()

    # --- TAB 4: TRADING DESK & PORTFOLIO ---
    def build_trading_tab(self):
        port_frame = ttk.LabelFrame(self.tab_trading, text="Your Live Portfolio", padding=10)
        port_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        summary_frame = ttk.Frame(port_frame)
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.lbl_cash = ttk.Label(summary_frame, text="Cash Balance: $0.00", font=("Arial", 14, "bold"), foreground="green")
        self.lbl_cash.pack(anchor=tk.W)
        self.lbl_holdings = ttk.Label(summary_frame, text="Holdings Value: $0.00", font=("Arial", 12))
        self.lbl_holdings.pack(anchor=tk.W)
        self.lbl_networth = ttk.Label(summary_frame, text="Total Net Worth: $0.00", font=("Arial", 14, "bold"), foreground="blue")
        self.lbl_networth.pack(anchor=tk.W, pady=5)

        cols = ("symbol", "shares", "live_price", "total_val")
        self.tree_port = ttk.Treeview(port_frame, columns=cols, show="headings", height=10)
        self.tree_port.heading("symbol", text="Ticker")
        self.tree_port.heading("shares", text="Shares Owned")
        self.tree_port.heading("live_price", text="Live Price")
        self.tree_port.heading("total_val", text="Total Value (USD)")
        self.tree_port.pack(fill=tk.BOTH, expand=True)

        trade_frame = ttk.LabelFrame(self.tab_trading, text="Execute Trade", padding=10)
        trade_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(trade_frame, text="Select Asset:", font=("Arial", 10, "bold")).pack(pady=(10, 2))
        all_trade_symbols = list(self.bist_map.keys()) + list(self.us_map.keys())
        self.combo_trade_stock = ttk.Combobox(trade_frame, values=all_trade_symbols, state="readonly", font=("Arial", 12))
        self.combo_trade_stock.current(0)
        self.combo_trade_stock.pack(pady=5)

        ttk.Label(trade_frame, text="Number of Shares:", font=("Arial", 10, "bold")).pack(pady=(10, 2))
        self.entry_trade_qty = ttk.Entry(trade_frame, font=("Arial", 12))
        self.entry_trade_qty.pack(pady=5)

        btn_box = ttk.Frame(trade_frame)
        btn_box.pack(pady=20)
        
        btn_buy = tk.Button(btn_box, text="BUY", bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), width=10, command=lambda: self.execute_trade("BUY"))
        btn_buy.pack(side=tk.LEFT, padx=10)
        
        btn_sell = tk.Button(btn_box, text="SELL", bg="#F44336", fg="white", font=("Arial", 12, "bold"), width=10, command=lambda: self.execute_trade("SELL"))
        btn_sell.pack(side=tk.LEFT, padx=10)
        
        self.lbl_trade_status = ttk.Label(trade_frame, text="", font=("Arial", 10, "italic"))
        self.lbl_trade_status.pack(pady=20)

    # ==========================================
    # TRADING ENGINE
    # ==========================================
    def execute_trade(self, action):
        ticker = self.combo_trade_stock.get()
        qty_str = self.entry_trade_qty.get()
        
        try:
            qty = float(qty_str)
            if qty <= 0: raise ValueError
        except ValueError:
            self.lbl_trade_status.config(text="❌ Invalid quantity!", foreground="red")
            return

        is_bist = ticker in self.bist_map
        yf_sym = self.bist_map.get(ticker) or self.us_map.get(ticker)
        
        live_price = self.live_prices.get(yf_sym, 0.0)
        usd_try_rate = self.live_prices.get("USDTRY=X", 32.50)
        
        if live_price == 0.0 or usd_try_rate == 0.0:
            self.lbl_trade_status.config(text="⏳ Waiting for live market data...", foreground="orange")
            return

        price_in_usd = live_price / usd_try_rate if is_bist else live_price
        total_usd_value = price_in_usd * qty
        
        current_cash = db.get_cash(self.user_id)
        portfolio = db.get_portfolio(self.user_id)
        current_shares = portfolio.get(ticker, 0.0)

        if action == "BUY":
            if current_cash >= total_usd_value:
                db.update_cash(self.user_id, current_cash - total_usd_value)
                db.update_portfolio(self.user_id, ticker, qty)
                self.lbl_trade_status.config(text=f"✅ Bought {qty} shares of {ticker} for ${total_usd_value:.2f}", foreground="green")
            else:
                self.lbl_trade_status.config(text=f"❌ Insufficient Funds! Need ${total_usd_value:.2f}", foreground="red")
        
        elif action == "SELL":
            if current_shares >= qty:
                db.update_cash(self.user_id, current_cash + total_usd_value)
                db.update_portfolio(self.user_id, ticker, -qty)
                self.lbl_trade_status.config(text=f"✅ Sold {qty} shares of {ticker} for ${total_usd_value:.2f}", foreground="green")
            else:
                self.lbl_trade_status.config(text=f"❌ Not enough shares! You own {current_shares}", foreground="red")
        
        self.entry_trade_qty.delete(0, tk.END)
        self.refresh_portfolio_data()

    def refresh_portfolio_data(self):
        if not self.user_id: return
        
        current_cash = db.get_cash(self.user_id)
        portfolio = db.get_portfolio(self.user_id)
        usd_try_rate = self.live_prices.get("USDTRY=X", 32.50)
        
        for row in self.tree_port.get_children():
            self.tree_port.delete(row)
            
        total_holdings_usd = 0.0
        
        for ticker, shares in portfolio.items():
            if shares <= 0: continue
            
            is_bist = ticker in self.bist_map
            yf_sym = self.bist_map.get(ticker) or self.us_map.get(ticker)
            live_price = self.live_prices.get(yf_sym, 0.0)
            
            if is_bist:
                price_usd = live_price / usd_try_rate if usd_try_rate > 0 else 0
                display_price = f"{live_price:.2f} ₺"
            else:
                price_usd = live_price
                display_price = f"${live_price:.2f}"
                
            total_val_usd = price_usd * shares
            total_holdings_usd += total_val_usd
            
            self.tree_port.insert("", tk.END, values=(ticker, f"{shares:.2f}", display_price, f"${total_val_usd:.2f}"))
            
        self.lbl_cash.config(text=f"Cash Balance: ${current_cash:,.2f}")
        self.lbl_holdings.config(text=f"Holdings Value: ${total_holdings_usd:,.2f}")
        self.lbl_networth.config(text=f"Total Net Worth: ${(current_cash + total_holdings_usd):,.2f}")

    # ==========================================
    # SUBSCRIPTIONS SYSTEM
    # ==========================================
    def add_subscription(self):
        name = self.entry_name.get().strip()
        amount_str = self.entry_amount.get().strip()
        currency = self.combo_currency.get()
        day_str = self.entry_day.get().strip()
        if not name or not amount_str or not day_str: return
        try: db.add_subscription(self.user_id, name, float(amount_str), currency, int(day_str))
        except: return
        self.refresh_sub_data()

    def delete_subscription(self):
        sel = self.tree_subs.selection()
        if sel: 
            db.delete_subscription(self.tree_subs.item(sel[0])['values'][0])
            self.refresh_sub_data()

    def refresh_sub_data(self):
        if not self.user_id: return
        for row in self.tree_subs.get_children(): self.tree_subs.delete(row)
        subs = db.get_all_subscriptions(self.user_id)
        
        live_usd_rate = self.live_prices.get("USDTRY=X", 32.50)
        if live_usd_rate == 0.0: live_usd_rate = 32.50
        total_try = 0.0

        for sub in subs:
            s_id, name, amount, currency, day = sub
            try_equiv = amount if currency == "TRY" else amount * live_usd_rate
            total_try += try_equiv
            self.tree_subs.insert("", tk.END, values=(s_id, name, f"{amount:.2f}", currency, day, f"{try_equiv:.2f} ₺"))

        self.lbl_monthly.config(text=f"Monthly Total: {total_try:,.2f} TRY")
        self.lbl_yearly.config(text=f"Yearly Total: {(total_try * 12):,.2f} TRY")

if __name__ == "__main__":
    root = tk.Tk()
    app = SubXApp(root)
    root.mainloop()