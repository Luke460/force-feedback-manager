import json
import os
import sys
import importlib.resources as pkg_resources
import tkinter as tk
import ctypes
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import ttkbootstrap as tb
from tkinter import filedialog

class Lut:
    def __init__(self):
        self.points = []

    def addPoint(self, x, y):
        self.points.append((x, y))

    def __str__(self):
        return "\n".join(f"{x:.3f}|{y:.5f}" for x, y in self.points)

def get_icon_path():
    ico_path = os.path.abspath('ico/FFM.ico')

    if os.path.exists(ico_path):
        return ico_path
    else:
        print("Error: FFM.ico not found!")
        return

def generateCustomLut(lutSize, deadZone, gain, power_boost):
    l = lutSize
    d = deadZone
    s = gain
    g = -power_boost/10
    lut = Lut()
    for i in range(l + 1):
        x = i
        y = x + (d * ((l - x) / l)) - (l - s) * (x / l) + (((((l / 2) - x) ** 2) / l) - (l / 4)) * ((g * 100) / l) * ((s / 100) - (d / 100))
        y = min(y, 100) # limit lut value
        lut.addPoint(round((i * 1.0) / (l * 1.0), 3), round(y * 0.01, 5))
    return lut

def get_padding_string(scaling_factor):
    if scaling_factor > 1.0:
        lateral_padding = 20
        top_padding = 0
        bottom_padding = 0
    else:
        lateral_padding = 30
        top_padding = 30
        bottom_padding = 10
    padding_string = str(lateral_padding) + " " + str(top_padding) + " " + str(lateral_padding) + " " + str(bottom_padding)
    return padding_string

def get_windows_scaling():
    """Get the current Windows scaling factor."""
    # Get the handle to the desktop window
    hdc = ctypes.windll.user32.GetDC(0)
    # Get the DPI for the screen
    dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
    # Calculate the scaling factor (default DPI is 96)
    scaling_factor = dpi / 96
    return scaling_factor

def limit_value(value, min, max):
    if value < min:
        return min
    elif value > max:
        return max
    return value

class ForceFeedbackManagerApp:
    def __init__(self, root):
        self.root = root
        self.version = "v1.0"
        self.title_string = "Force Feedback Manager - " + self.version
        self.root.title(self.title_string)
        print(self.title_string)
        
        # Create main frame
        scaling_factor = get_windows_scaling()
        padding_string = get_padding_string(scaling_factor)
        print("window padding: " + padding_string)
        mainframe = ttk.Frame(root, padding=padding_string)
        mainframe.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Initialize variables for sliders
        self.deadzone_value = tk.DoubleVar()
        self.max_output_value = tk.DoubleVar(value=100.0)
        self.power_boost_value = tk.DoubleVar(value=0.0)

        # Initialize limiters for values
        self.deadzone_min = 0.0
        self.deadzone_max = 30.0
        self.max_output_min = 50.0
        self.max_output_max = 150.0
        self.power_boost_min = 0.0
        self.power_boost_max = 10.0
        
        # Create sliders for FFB Deadzone, Max Output Force, and Power Boost
        self.create_slider_grid(mainframe)

        # Frame to hold the buttons
        button_frame = ttk.Frame(mainframe)
        button_frame.grid(row=6, column=0, columnspan=3, pady=20)

        # Apply button
        self.apply_button = ttk.Button(button_frame, text="Apply", command=self.apply_correction)
        self.apply_button.pack(side=tk.LEFT, padx=5)

        # Help button
        help_button = ttk.Button(button_frame, text="Help", command=self.show_help_popup)
        help_button.pack(side=tk.LEFT, padx=5)

        # Load Preset button
        load_preset_button = ttk.Button(button_frame, text="Load Preset", command=self.load_preset)
        load_preset_button.pack(side=tk.LEFT, padx=5)

        # Save Preset button
        save_preset_button = ttk.Button(button_frame, text="Save Preset", command=self.save_preset)
        save_preset_button.pack(side=tk.LEFT, padx=5)

        # Status label
        self.status_label = ttk.Label(mainframe, text="Adjust FFB Deadzone, Max Output Force, and Power Boost, then click Apply.")
        self.status_label.grid(row=7, column=0, columnspan=3, sticky=tk.W)
        
        # Create a frame to hold the chart and LUT output side by side
        chart_lut_frame = ttk.Frame(mainframe)
        chart_lut_frame.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        # Create chart for visual representation
        self.figure, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_lut_frame)
        self.canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.update_chart()
        
        # Text output for LUT with scrollbar
        self.lut_frame = ttk.Frame(chart_lut_frame)
        self.lut_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.lut_output = tk.Text(self.lut_frame, height=10, width=22)
        self.lut_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar = ttk.Scrollbar(self.lut_frame, orient=tk.VERTICAL, command=self.lut_output.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.lut_output.config(yscrollcommand=self.scrollbar.set)
        
        # Frame to hold the buttons
        final_button_frame = ttk.Frame(mainframe)
        final_button_frame.grid(row=9, column=0, columnspan=3, pady=20)

        # Donate button
        donate_button = ttk.Button(final_button_frame, text="How To Donate", command=self.show_donation_popup)
        donate_button.pack(side=tk.LEFT, padx=5)

        # Save button
        self.save_button = ttk.Button(final_button_frame, text="Save .lut", command=self.save_lut)
        self.save_button.pack(side=tk.LEFT, padx=5)

        # Update window size
        self.root.update_idletasks()
        mainframe.update_idletasks()
        mainframe_width = mainframe.winfo_width()
        mainframe_height = mainframe.winfo_height()

        # Adjust geometry based on the Windows scaling factor
        self.root.geometry(f"{int(mainframe_width * scaling_factor)}x{int(mainframe_height * scaling_factor)}")

        # Set the icon for the main window - this after the resize
        
        self.root.iconbitmap(get_icon_path())

        # Some logs
        print(f"Windows scaling factor: {scaling_factor * 100:.0f}%")
        print("Window resolution: " + str(mainframe_width) + " x " + str(mainframe_height))

    def save_preset(self):
        """Save the current slider values to a preset file."""
        preset = {
            "deadzone": self.deadzone_value.get(),
            "max_output": self.max_output_value.get(),
            "power_boost": self.power_boost_value.get()
        }
        
        if not os.path.exists("./presets"):
            os.makedirs("./presets")

        file_path = filedialog.asksaveasfilename(initialdir="./presets", defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if file_path:
            with open(file_path, "w") as file:
                json.dump(preset, file)
            self.status_label.config(text=f"Preset saved to {file_path}")

    def load_preset(self):
        """Load slider values from a preset file."""
        file_path = filedialog.askopenfilename(initialdir="./presets", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if file_path:
            with open(file_path, "r") as file:
                preset = json.load(file)
                self.deadzone_value.set(preset["deadzone"])
                self.max_output_value.set(preset["max_output"])
                self.power_boost_value.set(preset["power_boost"])
            self.apply_correction()
            self.status_label.config(text=f"Preset loaded from {file_path}")

    def center_popup(self, popup):
        """Center the given popup window on the root window."""
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()

        popup.update_idletasks()
        popup_width = popup.winfo_width()
        popup_height = popup.winfo_height()

        x = root_x + (root_width // 2) - (popup_width // 2)
        y = root_y + (root_height // 2) - (popup_height // 2)

        popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

    def show_help_popup(self):
        help_popup = tk.Toplevel(self.root)
        help_popup.title("Help - Settings Descriptions")
        help_popup.iconbitmap(get_icon_path())

        descriptions = {
            "FFB Deadzone": (
                "This setting compensates and removes the force feedback deadzone of some steering wheels that are not properly calibrated. "
                "It recovers the small forces that would otherwise be lost in the friction of gears, belts, or the motor itself. "
                "If set too high, vibrations may occur; reduce until they disappear. Increase until there's no more 'dead' feeling on straights."
            ),
            "Max Output Force": (
                "This setting limits the maximum power in case the steering wheel has difficulty accurately reproducing force feedback near its power limit. "
                "In most cases, it can be set to the default value of 100%. Many games/simulators have this setting. If you want to use this setting, keep the game's default value (usually 100%). "
                "Exceeding 100% is not recommended as it will introduce clipping. Instead, use the Power Boost setting."
            ),
            "Power Boost": (
                "This setting is beneficial for less powerful steering wheels to enhance the detail of weaker forces (which contain the most important force feedback information), "
                "gradually and progressively sacrificing stronger forces (such as strong impacts, pronounced bumps, which increase immersion but do not contain significant information). "
                "Some steering wheels have this setting integrated."
            )
        }
                
        for setting, description in descriptions.items():
            frame = ttk.Frame(help_popup)
            frame.pack(fill=tk.X, pady=10)
            # Use a bold font for the setting name and increase font size
            setting_label = ttk.Label(frame, text=f"{setting}:", font=('TkDefaultFont', 10, 'bold'))
            setting_label.pack(anchor=tk.W, padx=20, pady=5)
            # Increase font size for the description
            description_label = ttk.Label(frame, text=description, wraplength=500, justify=tk.LEFT, font=('TkDefaultFont', 10))
            description_label.pack(anchor=tk.W, padx=30)

        close_button = ttk.Button(help_popup, text="Close", command=help_popup.destroy)
        close_button.pack(pady=(10,15))

        self.center_popup(help_popup)

    def create_slider_grid(self, mainframe):
        slider_frame = ttk.Frame(mainframe)
        slider_frame.grid(row=0, column=0, sticky=(tk.E), padx=40, pady=10)
        
        for col in range(4):
            slider_frame.columnconfigure(col, weight=1)

        self.create_slider(slider_frame, "FFB Deadzone:", self.deadzone_value, 0, 0, from_=self.deadzone_min, to=self.deadzone_max)
        self.create_slider(slider_frame, "Max Output Force:", self.max_output_value, 1, 0, from_=self.max_output_min, to=self.max_output_max)
        self.create_slider(slider_frame, "Power Boost:", self.power_boost_value, 2, 0, from_=self.power_boost_min, to=self.power_boost_max)

    def create_slider(self, frame, text, variable, row, col, from_=0.0, to=100.0, increment=0.5):
        label = ttk.Label(frame, text=text)
        label.grid(row=row, column=col, sticky=tk.W, padx=5)
        
        slider = ttk.Scale(frame, from_=from_, to=to, orient=tk.HORIZONTAL, variable=variable, 
                        length=360,
                        command=lambda v: self.update_value(v, variable, increment))
        slider.grid(row=row, column=col+1, padx=5)
        
        entry = ttk.Entry(frame, textvariable=variable, width=10)
        entry.grid(row=row, column=col+2, padx=5)

        # Bind the Return key to the apply_correction method
        entry.bind("<Return>", lambda event: self.apply_correction() or self.apply_button.focus())
        
        reset_button = ttk.Button(frame, text="Reset", command=lambda: self.reset_slider(variable))
        reset_button.grid(row=row, column=col+3, padx=5)
        
        # Ensure the frame column expands with the window
        frame.columnconfigure(col, weight=1)
        frame.columnconfigure(col+1, weight=3)
        frame.columnconfigure(col+2, weight=1)
        frame.columnconfigure(col+3, weight=1)

        for child in frame.winfo_children():
            child.grid_configure(padx=6, pady=6)

    def reset_slider(self, variable):
        """Reset a single slider to its default value."""
        if variable == self.deadzone_value:
            variable.set(0.0)
        elif variable == self.max_output_value:
            variable.set(100.0)
        elif variable == self.power_boost_value:
            variable.set(0.0)
        self.update_chart()

    def update_value(self, value, variable, increment):
        """Update the slider value to the nearest increment and update the chart."""
        rounded_value = round(float(value) / increment) * increment
        variable.set(rounded_value)
        self.update_chart()

    def apply_correction(self, event=None):  # Add event=None to allow calling without event
        """Apply the deadzone and max output values to generate the LUT."""
        lut_size = 1000
        # Values check
        self.deadzone_value.set(limit_value(self.deadzone_value.get(), self.deadzone_min, self.deadzone_max))
        self.max_output_value.set(limit_value(self.max_output_value.get(), self.max_output_min, self.max_output_max))
        self.power_boost_value.set(limit_value(self.power_boost_value.get(), self.power_boost_min, self.power_boost_max))
        # Get values
        deadzone = self.deadzone_value.get()
        max_output = self.max_output_value.get()
        power_boost = self.power_boost_value.get()

        # Generate the LUT
        lut = generateCustomLut(lut_size, deadzone, max_output, power_boost)
        self.lut_output.delete(1.0, tk.END)
        # Insert "0.000|0.00000" as first row
        self.lut_output.insert(tk.END, "0.000|0.00000\n")

        # Write the rest of the LUT
        lut_content = str(lut).split("\n")[1:]
        self.lut_output.insert(tk.END, "\n".join(lut_content))
        self.status_label.config(text=f"FFB Deadzone set to {self.deadzone_value.get():.1f}%, Max Output Force set to {self.max_output_value.get():.1f}%, Power Boost set to {self.power_boost_value.get():.1f}")
        self.update_chart()

    def create_tooltip(self, event):
        """Create a tooltip showing the LUT values at the cursor position."""
        if event.inaxes == self.ax:
            for line in self.ax.get_lines():
                if line.contains(event)[0]:
                    xdata, ydata = line.get_data()
                    ind = line.contains(event)[1]["ind"][0]
                    x, y = xdata[ind], ydata[ind]
                    self.tooltip.set_text(f"{x:.3f}|{y:.3f}")
                    self.tooltip.xy = (event.xdata, event.ydata)
                    self.tooltip.set_visible(True)
                    self.canvas.draw_idle()
                    return
        self.tooltip.set_visible(False)
        self.canvas.draw_idle()
        
    def update_chart(self):
        """Update the chart with the current settings."""
        self.ax.clear()
        lut_size = 100
        deadzone = self.deadzone_value.get()
        max_output = self.max_output_value.get()
        power_boost = self.power_boost_value.get()
        
        lut = generateCustomLut(lut_size, deadzone, max_output, power_boost)
        x_vals = [x for x, y in lut.points]
        y_vals = [y for x, y in lut.points]
        
        line, = self.ax.plot(x_vals, y_vals, label='LUT Curve', color='blue', linewidth=2)
        
        # Find the intersection point of the LUT curve with the y-axis
        intersection_y = next((y for x, y in lut.points if x == 0), 0)
        
        # Add horizontal line for deadzone
        if deadzone > 0.0:
            self.ax.axhline(intersection_y, color='dimgrey', linestyle='--', label='Deadzone')
        
        # Find the maximum y value of the LUT curve
        max_y = max(y_vals)
        
        # Add horizontal line for max output force if less than 100
        if max_output < 100.0:
            self.ax.axhline(max_y, color='forestgreen', linestyle='--', label='Max Output Force')
        
        # Add vertical line for clipping if max_output >= 100.0
        if max_output > 100.0:
            clipping_point = next((x for x, y in lut.points if y >= 1.0), 1.0)
            self.ax.axvline(clipping_point, color='red', linestyle='--', label='Clipping')
        
        self.ax.set_ylim(0, 1)
        self.ax.set_xlim(0, 1)
        self.ax.set_xlabel('Input (%)')
        self.ax.set_ylabel('Output (%)')
        self.ax.legend()
        self.ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        self.ax.set_xticks(np.linspace(0, 1, 11))
        self.ax.set_yticks(np.linspace(0, 1, 11))
        self.ax.set_xticklabels([f'{int(i*100)}%' for i in np.linspace(0, 1, 11)])
        self.ax.set_yticklabels([f'{int(i*100)}%' for i in np.linspace(0, 1, 11)])
        
        # Create tooltip
        self.tooltip = self.ax.annotate("", xy=(0,0), xytext=(-20,20),
                                        textcoords="offset points",
                                        bbox=dict(boxstyle="round", fc="w"),
                                        arrowprops=dict(arrowstyle="->"))
        self.tooltip.set_visible(False)
        
        self.canvas.mpl_connect("motion_notify_event", self.create_tooltip)
        self.canvas.draw()
        
    def save_lut(self):
        """Save the LUT to a file."""
        # Apply the current settings before saving
        self.apply_correction()
        
        # Ensure the first line is always "0.000, 0.0000"
        lut_content = self.lut_output.get(1.0, tk.END)
        file_path = filedialog.asksaveasfilename(defaultextension=".lut", filetypes=[("LUT files", "*.lut"), ("All files", "*.*")])
        if file_path:
            with open(file_path, "w") as file:
                file.write(lut_content)
            self.status_label.config(text=f"LUT saved to {file_path}")
            self.show_donation_popup()

    def show_donation_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Support Force Feedback Manager")
        popup.iconbitmap(get_icon_path())

        label = ttk.Label(popup, text="Thank you for using Force Feedback Manager!\nIf you would like to support my work, please consider making a donation <3", font=('TkDefaultFont', 11))
        label.pack(pady=20, padx=20)

        button_frame = ttk.Frame(popup)
        button_frame.pack(pady=(0,20), padx=10)

        donation_button = ttk.Button(button_frame, text="Visit Donation Page", command=self.open_donation_link)
        donation_button.pack(side=tk.LEFT, padx=5)

        close_button = ttk.Button(button_frame, text="Close", command=popup.destroy)
        close_button.pack(side=tk.LEFT, padx=5)

        self.center_popup(popup)

    def open_donation_link(self):
        import webbrowser
        webbrowser.open("https://www.paypal.com/donate?hosted_button_id=WVSY5VX8TA4ZE")

    def on_closing(self):
        """Handle the window closing event."""
        self.root.destroy()
        sys.exit()

if __name__ == "__main__":
    root = tb.Window(themename="superhero")
    app = ForceFeedbackManagerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
