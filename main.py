import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import os
import threading
import time
from datetime import datetime

# Import the custom modules
from system_monitor import SystemMonitor
from llm_interaction import LLMInterface
from data_manager import DataManager

class GPUOCAdvisorApp:
    """
    Main application class for the GPU Overclocking Advisor with a Tkinter GUI.
    Provides system monitoring, LLM-powered recommendations, and data logging.
    """
    def __init__(self, master: tk.Tk, config_file: str = "config.json"):
        """
        Initializes the GUI application and its backend components.
        :param master: The root Tkinter window.
        :param config_file: Path to the configuration JSON file.
        """
        self.master = master
        self.master.title("LLM-Powered GPU OC Advisor")
        self.master.geometry("1000x800")
        self.master.resizable(True, True) # Allow resizing

        # Load configuration
        self.config_file = config_file
        self.config = self._load_config(config_file)

        # Initialize backend components
        self.monitor = SystemMonitor(self.config["gpu_brand"])
        self.llm_advisor = LLMInterface(self.config)
        self.data_manager = DataManager(self.config["app_data_dir"])
        self.current_metrics = {} # Stores the last fetched metrics

        # UI Theming and Mode
        self.dark_mode = False
        self._setup_styles()
        
        # Build the UI widgets FIRST
        self._create_widgets()
        
        # THEN apply the initial theme
        # _toggle_theme is called here, and it calls _apply_theme
        # so widgets must exist before this call
        self._toggle_theme() 

        self._start_metric_logging() # Start logging metrics in the background
        self.update_live_metrics_display() # Update display immediately

        # Recommendation tracking
        self.current_recommendation_id = None

        # Display initial safety warning
        self.master.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._show_safety_warning() # Show safety warning after protocol set up

    def _load_config(self, config_file: str) -> dict:
        """
        Loads configuration from a JSON file. If not found, creates a default.
        :param config_file: Path to the config file.
        :return: Loaded configuration dictionary.
        """
        if not os.path.exists(config_file):
            default_config = {
                "llm_model_name": "llama3", # IMPORTANT: Change this to your actual LLM model name
                "ollama_base_url": "http://localhost:11434",
                "gpu_brand": "NVIDIA", # IMPORTANT: Change to "NVIDIA" or "AMD"
                "target_temperature_celsius": 70,
                "priority": "efficiency", # or "hashrate", "longevity"
                "data_collection_interval_seconds": 10,
                "app_data_dir": "app_data"
            }
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            messagebox.showinfo("Config Created", f"Default '{config_file}' created. Please edit it with your GPU brand and LLM model before running the app effectively.")
            return default_config
        
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            messagebox.showerror("Config Error", f"Error reading '{config_file}'. Please ensure it's valid JSON.")
            return {} # Return empty to prevent further errors

    def _setup_styles(self):
        """Sets up Tkinter styles for light and dark modes."""
        self.styles = {
            "light": {
                "bg": "#f0f0f0", "fg": "#333333", "header_bg": "#e0e0e0", "header_fg": "#000000",
                "button_bg": "#e0e0e0", "button_fg": "#333333", "text_bg": "#ffffff", "text_fg": "#000000",
                "input_bg": "#ffffff", "input_fg": "#000000", "frame_bg": "#ffffff"
            },
            "dark": {
                "bg": "#2b2b2b", "fg": "#cccccc", "header_bg": "#3c3c3c", "header_fg": "#ffffff",
                "button_bg": "#4a4a4a", "button_fg": "#ffffff", "text_bg": "#1e1e1e", "text_fg": "#cccccc",
                "input_bg": "#333333", "input_fg": "#cccccc", "frame_bg": "#1e1e1e" # Adjusted input_fg to light grey for better contrast
            }
        }
        self.style = ttk.Style()
        # Set a base theme that is generally well-behaved, then customize
        self.style.theme_use("clam") # 'clam' often provides better cross-platform consistency

    def _apply_theme(self):
        """Applies the current light/dark theme to all widgets."""
        theme_colors = self.styles["dark"] if self.dark_mode else self.styles["light"]

        # Configure root window background directly
        self.master.config(bg=theme_colors["bg"])
        
        # Configure general ttk styles
        self.style.configure('.', background=theme_colors["bg"], foreground=theme_colors["fg"], font=('Arial', 10))
        
        # Specific styles for TFrame and TLabelframe
        self.style.configure('TFrame', background=theme_colors["frame_bg"])
        self.style.configure('TLabelframe', background=theme_colors["frame_bg"]) 
        self.style.configure('TLabelframe.Label', background=theme_colors["frame_bg"], foreground=theme_colors["fg"]) # For LabelFrame title text
        
        # Styles for TLabel (used for most labels)
        self.style.configure('TLabel', background=theme_colors["frame_bg"], foreground=theme_colors["fg"])

        # --- GUARANTEED BUTTON TEXT VISIBILITY ---
        # Using .map for TButton to ensure state-dependent foreground and background changes
        self.style.map('TButton',
                       background=[('active', theme_colors["button_bg"]), ('!disabled', theme_colors["button_bg"])],
                       foreground=[('active', theme_colors["button_fg"]), ('!disabled', theme_colors["button_fg"])],
                       font=[('active', ('Arial', 10, 'bold')), ('!disabled', ('Arial', 10, 'bold'))],
                       relief=[('pressed', 'sunken'), ('!pressed', 'raised')]) # Added visual feedback on press
        self.style.configure('TButton', borderwidth=2) # Consistent border

        # Configure Header.TLabel style (used by title and status bar)
        self.style.configure('Header.TLabel', background=theme_colors["header_bg"], foreground=theme_colors["header_fg"], font=('Arial', 14, 'bold'))
        
        # --- GUARANTEED ENTRY TEXT VISIBILITY ---
        # Using .map for TEntry to ensure state-dependent fieldbackground and foreground changes
        self.style.map('TEntry',
                       fieldbackground=[('readonly', theme_colors["input_bg"]), ('!readonly', theme_colors["input_bg"])],
                       foreground=[('readonly', theme_colors["input_fg"]), ('!readonly', theme_colors["input_fg"])])
        self.style.configure('TEntry', font=('Arial', 10))


        # Directly configure scrolledtext for colors (these are not ttk widgets)
        self.metrics_display.configure(bg=theme_colors["text_bg"], fg=theme_colors["text_fg"])
        self.llm_output_display.configure(bg=theme_colors["text_bg"], fg=theme_colors["text_fg"])
        
        # Apply theme to notes_text in the update dialog if it's open
        for widget in self.master.winfo_children():
            if isinstance(widget, tk.Toplevel):
                # Recursively apply theme to all children of Toplevels, focusing on scrolledtext widgets
                self._apply_theme_to_children(widget, theme_colors)

    def _apply_theme_to_children(self, parent_widget, theme_colors):
        """Helper to recursively apply theme to children widgets, specifically scrolledtext."""
        for child in parent_widget.winfo_children():
            if isinstance(child, scrolledtext.ScrolledText):
                child.configure(bg=theme_colors["input_bg"], fg=theme_colors["input_fg"])
            elif hasattr(child, 'winfo_children'): # Recurse into containers
                self._apply_theme_to_children(child, theme_colors)

    def _toggle_theme(self):
        """Toggles between light and dark modes."""
        self.dark_mode = not self.dark_mode
        self._apply_theme()
        theme_name = "Dark" if self.dark_mode else "Light"
        self.theme_button.config(text=f"{theme_name} Mode")

    def _create_widgets(self):
        """Creates and lays out all GUI widgets."""
        main_frame = ttk.Frame(self.master, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Header Frame ---
        header_frame = ttk.Frame(main_frame, style='TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 15))

        title_label = ttk.Label(header_frame, text="LLM-Powered GPU OC Advisor", style='Header.TLabel')
        title_label.pack(side=tk.LEFT, padx=(0, 30))

        self.theme_button = ttk.Button(header_frame, text="Light Mode", command=self._toggle_theme, style='TButton')
        self.theme_button.pack(side=tk.RIGHT)

        # --- Main Content Area (Panedwindow for resizable sections) ---
        content_pane = ttk.Panedwindow(main_frame, orient=tk.HORIZONTAL)
        content_pane.pack(fill=tk.BOTH, expand=True)

        # Left Frame: Metrics and Inputs
        left_frame = ttk.Frame(content_pane, style='TFrame', padding="15")
        content_pane.add(left_frame, weight=1)

        # Right Frame: LLM Output
        right_frame = ttk.Frame(content_pane, style='TFrame', padding="15")
        content_pane.add(right_frame, weight=1)

        # --- Left Frame Content ---
        # Current Metrics Display
        metrics_label = ttk.Label(left_frame, text="Current System Metrics:", style='TLabel')
        metrics_label.pack(fill=tk.X, pady=(0, 8))
        self.metrics_display = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, height=15, state='disabled', font=('Arial', 10))
        self.metrics_display.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Input for LLM Recommendation
        input_frame = ttk.LabelFrame(left_frame, text="Get New Recommendation", style='TLabelframe', padding="15")
        input_frame.pack(fill=tk.X, pady=(0, 15))

        # Labels for input fields - these will be styled by 'TLabel'
        ttk.Label(input_frame, text="Mining Algorithm:", style='TLabel').grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.algo_entry = ttk.Entry(input_frame, width=30, style='TEntry')
        self.algo_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        self.algo_entry.insert(0, "Ethash") # Default value

        ttk.Label(input_frame, text="Optimization Goal:", style='TLabel').grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.goal_entry = ttk.Entry(input_frame, width=30, style='TEntry')
        self.goal_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        self.goal_entry.insert(0, self.config['priority']) # Default from config

        self.get_rec_button = ttk.Button(input_frame, text="Get Recommendation", command=self._get_new_recommendation_threaded, style='TButton')
        self.get_rec_button.grid(row=2, column=0, columnspan=2, pady=15)

        input_frame.grid_columnconfigure(1, weight=1) # Make entry field expand

        # Past Recommendations Button
        self.view_past_rec_button = ttk.Button(left_frame, text="View Past Recommendations", command=self._view_past_recommendations, style='TButton')
        self.view_past_rec_button.pack(fill=tk.X, pady=(0, 8))

        self.update_rec_status_button = ttk.Button(left_frame, text="Update Recommendation Status", command=self._show_update_status_dialog, style='TButton')
        self.update_rec_status_button.pack(fill=tk.X, pady=(0, 8))
        
        self.fine_tune_guidance_button = ttk.Button(left_frame, text="LLM Fine-tuning Guidance", command=self._display_fine_tuning_guidance, style='TButton')
        self.fine_tune_guidance_button.pack(fill=tk.X, pady=(0, 8))

        # --- Right Frame Content (LLM Output) ---
        llm_output_label = ttk.Label(right_frame, text="LLM Overclocking Recommendation:", style='TLabel')
        llm_output_label.pack(fill=tk.X, pady=(0, 8))
        self.llm_output_display = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, height=30, state='disabled', font=('Arial', 10))
        self.llm_output_display.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # --- Status Bar ---
        self.status_bar = ttk.Label(self.master, text="Ready.", relief=tk.SUNKEN, anchor=tk.W, style='Header.TLabel')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _show_safety_warning(self):
        """Displays a critical safety warning to the user."""
        messagebox.showwarning(
            "CRITICAL SAFETY WARNING",
            "GPU overclocking carries inherent risks, including system instability, crashes, and potential hardware damage.\n\n"
            "This application provides AI-generated recommendations based on its knowledge base. It DOES NOT GUARANTEE SAFETY OR OPTIMAL PERFORMANCE.\n\n"
            "ALWAYS apply changes incrementally, monitor your system closely (temperatures, stability), and proceed with extreme caution. You are solely responsible for any consequences of applying these recommendations."
        )

    def _on_closing(self):
        """Handles application closing, ensuring background threads are stopped."""
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            self.stop_logging = True # Signal the background thread to stop
            # Give a moment for the thread to recognize the signal (optional, but good practice)
            time.sleep(0.1) 
            self.master.destroy()

    def update_status(self, message: str):
        """Updates the message in the status bar."""
        self.status_bar.config(text=message)
        self.master.update_idletasks() # Ensure UI updates immediately

    def update_metrics_display(self, metrics_string: str):
        """Updates the scrolled text widget with current metrics."""
        self.metrics_display.config(state='normal')
        self.metrics_display.delete(1.0, tk.END)
        self.metrics_display.insert(tk.END, metrics_string)
        self.metrics_display.config(state='disabled')

    def update_llm_output_display(self, output_text: str):
        """Updates the scrolled text widget with LLM output."""
        self.llm_output_display.config(state='normal')
        self.llm_output_display.delete(1.0, tk.END)
        self.llm_output_display.insert(tk.END, output_text)
        self.llm_output_display.config(state='disabled')

    def update_live_metrics_display(self):
        """Fetches and displays current metrics, logs them, and schedules next update."""
        try:
            self.current_metrics = self.monitor.get_realtime_metrics()
            metrics_string = self.monitor.get_system_summary_string(self.current_metrics)
            self.update_metrics_display(metrics_string)
            self.data_manager.log_metrics(self.current_metrics) # Log for history
        except Exception as e:
            self.update_status(f"Error updating metrics: {e}")
        
        # Schedule the next update
        self.master.after(self.config["data_collection_interval_seconds"] * 1000, self.update_live_metrics_display)

    def _start_metric_logging(self):
        """Starts a background thread for continuous metric logging."""
        self.stop_logging = False
        self.logging_thread = threading.Thread(target=self._continuous_metric_logging, daemon=True)
        self.logging_thread.start()

    def _continuous_metric_logging(self):
        """Background task to continuously log metrics."""
        while not self.stop_logging:
            try:
                metrics = self.monitor.get_realtime_metrics()
                self.data_manager.log_metrics(metrics)
            except Exception as e:
                print(f"Background logging error: {e}") # Print error to console for debugging
            time.sleep(self.config["data_collection_interval_seconds"])

    def _get_new_recommendation_threaded(self):
        """Starts a new thread to get LLM recommendation to prevent UI freeze."""
        self.update_status("Generating recommendation... Please wait. This may take a few moments.")
        self.get_rec_button.config(state='disabled') # Disable button during generation
        self.master.update_idletasks() # Force UI update
        
        algorithm = self.algo_entry.get().strip()
        goal = self.goal_entry.get().strip()
        if not algorithm:
            messagebox.showerror("Input Error", "Please enter a mining algorithm.")
            self.get_rec_button.config(state='normal')
            self.update_status("Ready.")
            return
        if not goal:
            goal = self.config['priority'] # Use default if empty

        # Pass current metrics as snapshot to LLM thread
        current_metrics_snapshot = self.current_metrics.copy()
        system_summary_snapshot = self.monitor.get_system_summary_string(current_metrics_snapshot)

        threading.Thread(target=self._fetch_recommendation_task, 
                         args=(system_summary_snapshot, current_metrics_snapshot, algorithm, goal),
                         daemon=True).start()

    def _fetch_recommendation_task(self, system_summary: str, metrics_at_rec: dict, algorithm: str, goal: str):
        """Background task to fetch recommendation from LLM."""
        try:
            llm_recommendation_text = self.llm_advisor.get_overclock_recommendations(
                system_summary, algorithm, goal
            )
            self.master.after(0, self._display_recommendation, llm_recommendation_text, metrics_at_rec, algorithm, goal)
        except Exception as e:
            self.master.after(0, self.update_status, f"Error getting LLM recommendation: {e}")
            self.master.after(0, self.get_rec_button.config, {'state': 'normal'})

    def _display_recommendation(self, llm_recommendation_text: str, metrics_at_rec: dict, algorithm: str, goal: str):
        """Displays LLM recommendation and saves it."""
        self.update_llm_output_display(llm_recommendation_text)
        self.current_recommendation_id = self.data_manager.save_recommendation(
            llm_recommendation_text, metrics_at_rec, goal, algorithm
        )
        self.update_status(f"Recommendation generated and saved. ID: {self.current_recommendation_id}")
        self.get_rec_button.config(state='normal') # Re-enable button

    def _view_past_recommendations(self):
        """Displays a new window with past recommendations."""
        past_recs = self.data_manager.load_all_recommendations()
        
        # Create a new top-level window
        recs_window = tk.Toplevel(self.master)
        recs_window.title("Past Recommendations")
        recs_window.geometry("800x600")
        recs_window.transient(self.master) # Make it appear on top of the main window
        recs_window.grab_set() # Disable interaction with the main window until this is closed

        recs_window.config(bg=self.styles["dark"]["bg"] if self.dark_mode else self.styles["light"]["bg"])

        # Use a Treeview widget for better display of tabular data
        tree_frame = ttk.Frame(recs_window, padding="10", style='TFrame')
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(tree_frame, columns=("ID", "Date", "Goal", "Algorithm", "Status"), show="headings")
        tree.heading("ID", text="ID")
        tree.heading("Date", text="Date")
        tree.heading("Goal", text="Goal")
        tree.heading("Algorithm", text="Algorithm")
        tree.heading("Status", text="Status")

        # Configure column widths (adjust as needed)
        tree.column("ID", width=100, anchor=tk.CENTER)
        tree.column("Date", width=150, anchor=tk.CENTER)
        tree.column("Goal", width=150)
        tree.column("Algorithm", width=100, anchor=tk.CENTER)
        tree.column("Status", width=100, anchor=tk.CENTER)
        
        # Add a scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)

        if not past_recs:
            tree.insert("", tk.END, values=("", "", "No recommendations found.", "", ""))
        else:
            for rec in past_recs:
                status_text = rec.get('applied_status', 'N/A')
                tree.insert("", tk.END, values=(
                    rec.get('id', 'N/A'),
                    datetime.fromisoformat(rec['timestamp']).strftime('%Y-%m-%d %H:%M') if 'timestamp' in rec else 'N/A',
                    rec.get('user_goal', 'N/A'),
                    rec.get('mining_algorithm', 'N/A'),
                    status_text
                ))
        
        # Add a button to view details of selected recommendation
        details_button = ttk.Button(tree_frame, text="View Details", command=lambda: self._show_recommendation_details(tree), style='TButton')
        details_button.pack(pady=10)

        recs_window.wait_window(recs_window) # Wait until the window is closed

    def _show_recommendation_details(self, tree_widget: ttk.Treeview):
        """Displays full details of a selected recommendation."""
        selected_item = tree_widget.selection()
        if not selected_item:
            messagebox.showinfo("No Selection", "Please select a recommendation to view details.")
            return

        item_values = tree_widget.item(selected_item, 'values')
        rec_id = item_values[0] # The ID is the first column

        rec_data = self.data_manager.load_recommendation(rec_id)
        if not rec_data:
            messagebox.showerror("Error", "Could not load recommendation details.")
            return

        detail_window = tk.Toplevel(self.master)
        detail_window.title(f"Recommendation Details: {rec_id}")
        detail_window.geometry("700x700")
        detail_window.transient(self.master)
        detail_window.grab_set()

        detail_window.config(bg=self.styles["dark"]["bg"] if self.dark_mode else self.styles["light"]["bg"])

        detail_text = scrolledtext.ScrolledText(detail_window, wrap=tk.WORD, state='disabled', font=('Arial', 10))
        detail_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        content = f"Recommendation ID: {rec_data.get('id', 'N/A')}\n" \
                  f"Timestamp: {rec_data.get('timestamp', 'N/A')}\n" \
                  f"User Goal: {rec_data.get('user_goal', 'N/A')}\n" \
                  f"Mining Algorithm: {rec_data.get('mining_algorithm', 'N/A')}\n" \
                  f"Status: {rec_data.get('applied_status', 'N/A')}\n\n" \
                  f"--- System Snapshot at Recommendation Time ---\n" \
                  f"{json.dumps(rec_data.get('system_snapshot_at_recommendation', {}), indent=2)}\n\n" \
                  f"--- LLM's Recommendation ---\n" \
                  f"{rec_data.get('llm_recommendation_text', 'No recommendation text found.')}\n\n"
        
        actual_perf = rec_data.get('actual_performance_after_apply', {})
        if actual_perf:
            content += f"--- Actual Performance After Apply ---\n" \
                       f"{json.dumps(actual_perf, indent=2)}\n\n"
        
        user_notes = rec_data.get('user_notes', '')
        if user_notes:
            content += f"--- User Notes ---\n" \
                       f"{user_notes}\n\n"

        detail_text.config(state='normal')
        detail_text.insert(tk.END, content)
        detail_text.config(state='disabled')

        close_button = ttk.Button(detail_window, text="Close", command=detail_window.destroy, style='TButton')
        close_button.pack(pady=5)

    def _show_update_status_dialog(self):
        """Displays a dialog for updating recommendation status."""
        update_dialog = tk.Toplevel(self.master)
        update_dialog.title("Update Recommendation Status")
        update_dialog.geometry("400x350") # Slightly increased height for notes
        update_dialog.transient(self.master)
        update_dialog.grab_set()
        # Set background for Toplevel window directly
        update_dialog.config(bg=self.styles["dark"]["bg"] if self.dark_mode else self.styles["light"]["bg"])

        frame = ttk.Frame(update_dialog, padding="10", style='TFrame')
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Recommendation ID:", style='TLabel').grid(row=0, column=0, sticky=tk.W, pady=2)
        rec_id_entry = ttk.Entry(frame, width=30, style='TEntry')
        rec_id_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        # Pre-fill if there's a last generated ID
        if self.current_recommendation_id:
            rec_id_entry.insert(0, self.current_recommendation_id)

        ttk.Label(frame, text="New Status:", style='TLabel').grid(row=1, column=0, sticky=tk.W, pady=2)
        status_options = ["APPLIED", "FAILED", "REVERTED", "CANCELLED"]
        status_var = tk.StringVar(frame)
        status_var.set(status_options[0]) # default value
        status_menu = ttk.OptionMenu(frame, status_var, status_options[0], *status_options)
        status_menu.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)

        ttk.Label(frame, text="Observed Hash Rate (MH/s):", style='TLabel').grid(row=2, column=0, sticky=tk.W, pady=2)
        hash_rate_entry = ttk.Entry(frame, width=30, style='TEntry')
        hash_rate_entry.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)

        ttk.Label(frame, text="Observed Power (W):", style='TLabel').grid(row=3, column=0, sticky=tk.W, pady=2)
        power_entry = ttk.Entry(frame, width=30, style='TEntry')
        power_entry.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=2)
        
        ttk.Label(frame, text="Your Notes:", style='TLabel').grid(row=4, column=0, sticky=tk.W, pady=2)
        notes_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=4, font=('Arial', 9))
        notes_text.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=2)
        # Configure notes_text colors directly, as it's a scrolledtext widget
        notes_text.configure(bg=self.styles["dark"]["input_bg"] if self.dark_mode else self.styles["light"]["input_bg"])
        notes_text.configure(fg=self.styles["dark"]["input_fg"] if self.dark_mode else self.styles["light"]["input_fg"])


        def apply_update():
            rec_id = rec_id_entry.get().strip()
            new_status = status_var.get()
            actual_hash_rate = hash_rate_entry.get().strip()
            actual_power = power_entry.get().strip()
            notes = notes_text.get(1.0, tk.END).strip()

            actual_metrics = {}
            if actual_hash_rate:
                try: actual_metrics["gpu"] = {"hash_rate_mhps": float(actual_hash_rate)}
                except ValueError: pass
            if actual_power:
                try: actual_metrics.setdefault("gpu", {})["power_draw_watts"] = float(actual_power)
                except ValueError: pass
            
            # Add other relevant actual metrics if needed (e.g., current temp snapshot)
            if actual_metrics and "gpu" in actual_metrics: # Ensure we capture current temps etc.
                 current_metrics_snapshot = self.monitor.get_realtime_metrics().get("gpu", {})
                 actual_metrics["gpu"].update(current_metrics_snapshot)


            if not rec_id:
                messagebox.showerror("Input Error", "Please enter a Recommendation ID.")
                return

            self.data_manager.update_recommendation_status(rec_id, new_status, actual_metrics, notes)
            messagebox.showinfo("Status Updated", f"Recommendation {rec_id} status changed to {new_status}.")
            update_dialog.destroy()
            self.update_status(f"Recommendation {rec_id} status changed to {new_status}.")


        update_button = ttk.Button(frame, text="Update Status", command=apply_update, style='TButton')
        update_button.grid(row=5, column=0, columnspan=2, pady=10)

        frame.grid_columnconfigure(1, weight=1)

        update_dialog.wait_window(update_dialog)


    def _display_fine_tuning_guidance(self):
        """Displays guidance for LLM fine-tuning in a new window."""
        guidance_window = tk.Toplevel(self.master)
        guidance_window.title("LLM Fine-tuning Guidance")
        guidance_window.geometry("700x500")
        guidance_window.transient(self.master)
        guidance_window.grab_set()
        # Set background for Toplevel window directly
        guidance_window.config(bg=self.styles["dark"]["bg"] if self.dark_mode else self.styles["light"]["bg"])

        guidance_text_content = """
        --- LLM Fine-tuning Guidance ---

        To significantly improve the LLM's accuracy and tailor it to your specific hardware and mining habits over time:

        1.  **Collect Data:** As you use this tool and update recommendation statuses (especially 'APPLIED' and 'FAILED'), the `app_data/recommendations/` directory will accumulate JSON files containing:
            * The LLM's original recommendation.
            * The system's state when the recommendation was given.
            * The actual performance/outcome after applying the settings.
            * Your notes on stability or issues.

        2.  **Curate Feedback:**
            * **Successes (APPLIED):** These are positive examples. The LLM's prompt and its successful recommendation (along with actual performance data) can reinforce good patterns.
            * **Failures (FAILED/REVERTED):** These are critical learning opportunities. Review these cases and try to identify *why* the recommendation was suboptimal (e.g., too aggressive, missed a crucial detail, instability).

        3.  **Create Training Examples:** Transform these curated experiences into question-and-answer pairs or instruction-following examples for the LLM.
            * **Example for a 'FAILED' scenario:**
                * **Input (Prompt):** "You previously recommended [LLM_REC_TEXT] for my [GPU_MODEL] on [ALGORITHM] when its state was [SYSTEM_SNAPSHOT]. This resulted in [ACTUAL_OUTCOME_DETAILS, e.g., 'a system crash due to unstable memory clock']. Given this outcome, what specific adjustment would you make to your reasoning or the recommended settings for this scenario in the future? Provide revised settings and reasoning."
                * **Output (Corrected LLM behavior):** "[REVISED_SAFE_RECOMMENDATION] because [EXPLAIN_WHY_PREVIOUS_FAILED_AND_NEW_IS_BETTER]."
            * **Example for a 'SUCCESS' scenario:**
                * **Input (Prompt): "You recommended [LLM_REC_TEXT] for my [GPU_MODEL] on [ALGORITHM] when its state was [SYSTEM_SNAPSHOT]. This achieved [ACTUAL_OUTCOME_DETAILS, e.g., '60 MH/s at 120W, very stable']. Explain why these settings were effective and what positive indicators you saw."
                * **Output (Reinforcement):** "[DETAILED_EXPLANATION_OF_SUCCESSFUL_REASONING]."

        4.  **Fine-tune with LoRA (Parameter-Efficient Fine-Tuning):**
            * LoRA allows you to train a small "adapter" on top of your existing large local LLM without retraining the entire model, making it much more feasible on consumer hardware.
            * **Tools:**
                * **`peft` library (Hugging Face):** A popular choice for LoRA fine-tuning in Python.
                * **Ollama's Fine-tuning (Emerging):** Ollama is developing built-in fine-tuning capabilities that might simplify this further. Keep an eye on their documentation.
                * **`unsloth`:** A highly optimized library that can make LoRA fine-tuning significantly faster.
            * **Process:** Convert your curated Q&A data into a dataset compatible with `peft` (often JSONL format). Load your base LLM (e.g., Llama 3) and attach a LoRA adapter. Train for a few epochs.
            * **Integration:** Once fine-tuned, you'll typically load your base LLM and then load the LoRA adapter. The LLM will then use the combined knowledge.

        This iterative process of collecting feedback, curating data, and performing targeted fine-tuning will progressively make your LLM an increasingly precise and personalized overclocking expert for your unique setup.
        """
        guidance_text = scrolledtext.ScrolledText(guidance_window, wrap=tk.WORD, state='disabled', font=('Arial', 10))
        guidance_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # Configure guidance_text colors directly, as it's a scrolledtext widget
        guidance_text.config(bg=self.styles["dark"]["text_bg"] if self.dark_mode else self.styles["light"]["text_bg"])
        guidance_text.config(fg=self.styles["dark"]["text_fg"] if self.dark_mode else self.styles["light"]["text_fg"])
        
        guidance_text.config(state='normal')
        guidance_text.insert(tk.END, guidance_text_content)
        guidance_text.config(state='disabled')

        close_button = ttk.Button(guidance_window, text="Close", command=guidance_window.destroy, style='TButton')
        close_button.pack(pady=5)


if __name__ == "__main__":
    root = tk.Tk()
    app = GPUOCAdvisorApp(root)
    root.mainloop()
