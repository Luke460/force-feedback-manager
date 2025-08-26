import ctypes
import json
import os
import sys
import webbrowser
import requests
import tkinter as tk

from tkinter import filedialog
from tkinter import ttk

import matplotlib.pyplot as plt
import numpy as np
import ttkbootstrap as tb
from ttkbootstrap import Style
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk

class Lut:
    """Define a LUT object (or lookup table)."""

    def __init__(self):
        self.points = []

    def addPoint(self, x, y):
        """Add a point to the LUT."""
        self.points.append((x, y))

    def __str__(self):
        """Get the icon path checking if it exists."""
        return "\n".join(f"{x:.3f}|{y:.5f}" for x, y in self.points)

def open_link(link):
        import webbrowser
        webbrowser.open(link)

def get_icon_path():
    """Get the icon path checking if exists."""
    ico_path = os.path.abspath('ico/FFM.ico')

    if os.path.exists(ico_path):
        return ico_path
    else:
        print("Error: FFM.ico not found!")
        return

def generateCustomLut(lutSize, deadZone, gain, power_boost):
    """Generate a custom LUT using the given parameters."""
    l = lutSize
    d = deadZone
    s = gain
    g = -power_boost/10
    lut = Lut()
    for i in range(l + 1):
        x = i
        # This was the hardest part of all the application by far. So many time to get to this formula.
        y = x + (d * ((l - x) / l)) - (l - s) * (x / l) + (((((l / 2) - x) ** 2) / l) - (l / 4)) * ((g * 100) / l) * ((s / 100) - (d / 100))
        y = min(y, 100) # limit lut value
        lut.addPoint(round((i * 1.0) / (l * 1.0), 3), round(y * 0.01, 5))
    return lut

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
    """Force a value to be between min and max."""
    if value < min:
        return min
    elif value > max:
        return max
    return value


class ForceFeedbackManagerApp:

    def __init__(self, root):
        """Initialize the application."""
        self.root = root
        self.version = "v1.1.9"
        self.title_string = "Force Feedback Manager - " + self.version
        self.root.title(self.title_string)
        self.compare_lut = None
        self.compare_lut_modified = False
        self.loaded_preset_name = None
        self.saved_lut_name = None
        self.compare_lut_name = None

        print(self.title_string)

        self.load_donation_image()
        
        # Create main frame
        lateral_padding = 30
        top_padding = 30
        bottom_padding = 10
        padding_string = str(lateral_padding) + " " + str(top_padding) + " " + str(lateral_padding) + " " + str(bottom_padding)
        mainframe = ttk.Frame(root, padding=padding_string)
        mainframe.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        row = 0

        # Main label
        self.main_title_label = ttk.Label(mainframe, text="Force Feedback Manager", font=('Helvetica', 20, 'bold italic'))
        self.main_title_label.grid(row=row, column=0, columnspan=3, pady=5)
        update_check_button = ttk.Button(mainframe, text="Check Updates", command=self.check_version)
        update_check_button.grid(row=row, column=0, sticky=tk.W, padx=5)
        donate_button = self.create_donation_button(mainframe, self.show_donation_popup)
        donate_button.grid(row=row, column=2, sticky=tk.E, padx=5)
        row += 1

        # Secondary label
        self.secondary_title_label = ttk.Label(mainframe, text="Customize your driving simulation experience", font=('Helvetica', 12, 'italic'))
        self.secondary_title_label.grid(row=row, column=0, columnspan=3, pady=15)
        row += 1

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
        self.create_slider_grid(mainframe, starting_row=row)
        row += 4  # Adjust based on the number of rows used in create_slider_grid

        # Frame to hold the buttons
        button_frame = ttk.Frame(mainframe)
        button_frame.grid(row=row, column=0, columnspan=3, pady=20)
        row += 1

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
        self.status_label.grid(row=row, column=0, columnspan=3, sticky=tk.W)
        row += 1
        
        # Create a frame to hold the chart and LUT output side by side
        chart_lut_frame = ttk.Frame(mainframe)
        chart_lut_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E))
        row += 1
        
        # Create chart for visual representation
        self.figure, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_lut_frame)
        self.canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.update_chart()

        # Text output for LUT with comparison option and related scrollbar
        self.lut_frame = ttk.Frame(chart_lut_frame)
        self.lut_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.combined_output = tk.Text(self.lut_frame, height=10, width=20, state=tk.DISABLED)
        self.combined_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar = ttk.Scrollbar(self.lut_frame, orient=tk.VERTICAL, command=self.combined_output.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.combined_output.config(yscrollcommand=self.scrollbar.set)

        # Frame to hold the buttons
        final_button_frame = ttk.Frame(mainframe)
        final_button_frame.grid(row=row, column=0, columnspan=3, pady=20)

        # Compare button
        compare_button = ttk.Button(final_button_frame, text="Compare LUT", command=self.load_compare_lut)
        compare_button.pack(side=tk.LEFT, padx=5)

        # Clear Compare button
        clear_compare_button = ttk.Button(final_button_frame, text="Clear Comparison", command=self.clear_comparison)
        clear_compare_button.pack(side=tk.LEFT, padx=5)

        # Save button
        self.save_button = ttk.Button(final_button_frame, text="Save LUT", command=self.save_lut)
        self.save_button.pack(side=tk.LEFT, padx=5)

        # Update window size
        self.root.update_idletasks()
        mainframe.update_idletasks()
        mainframe_width = mainframe.winfo_width()
        mainframe_height = mainframe.winfo_height()

        # Apply the adjusted scaling factors
        scaling_factor = get_windows_scaling()
        adjusted_width = int(mainframe_width * (scaling_factor - (scaling_factor - 1.0) * 0.25))
        adjusted_height = int(mainframe_height * (scaling_factor - (scaling_factor - 1.0) * 0.5))
        self.root.geometry(f"{adjusted_width}x{adjusted_height}")

        # Set the icon for the main window - this after the resize
        
        self.root.iconbitmap(get_icon_path())

        # Some logs
        print(f"Windows scaling factor: {scaling_factor * 100:.0f}%")
        print("Window resolution: " + str(mainframe_width) + " x " + str(mainframe_height))

        # Update check
        self.root.after(1000, lambda: self.check_version(show_up_to_date=False))

    def check_version(self, show_up_to_date=True):
        latest = self.get_latest_release()
        message = None
        new_version = False
        if latest is None:
            message = "Unable to check the latest version"
        elif latest != self.version:
            message = f"⚠️ A new update is available: {latest}"
            new_version = True
        elif show_up_to_date:
            message = "✅ Force Feedback Manager is up to date."
        if message:
            print(message)
            self.show_update_popup(message, new_version)

    def get_latest_release(self):
        url = "https://api.github.com/repos/Luke460/force-feedback-manager/releases/latest"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['tag_name']
        return None

    def show_update_popup(self, message, new_version):
        popup = tk.Toplevel(self.root)
        popup.title("Update Check")
        popup.iconbitmap(get_icon_path())

        label = ttk.Label(popup, text=message, font=('TkDefaultFont', 11))
        label.pack(pady=20, padx=20)

        if new_version:
            link = "https://github.com/Luke460/force-feedback-manager/releases/latest";
            button_frame = ttk.Frame(popup)
            button_frame.pack(pady=(0,20), padx=10)
            update_button = ttk.Button(button_frame, text="Update", command=lambda: open_link(link))
            update_button.pack(side=tk.LEFT, padx=5)

        self.center_popup(popup)

    def create_donation_button(self, mainframe, command):
        """Create a frame for the donation button in the top right corner."""
        if self.paypal_image:
            style = Style(theme='superhero')
            background_color = style.colors.get('bg')
            style.configure('Transparent.TButton', background=background_color, borderwidth=0, highlightthickness=0, relief='flat', focuscolor='none')
            donate_button = ttk.Button(mainframe, image=self.paypal_image, command=command, style='Transparent.TButton')
        else:
            donate_button = ttk.Button(mainframe, text="Donate <3", command=self.show_donation_popup)
        return donate_button

    def load_donation_image(self):
        """Load donation button image."""
        try:
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            scaling_factor = get_windows_scaling()

            new_width = int(100 * scaling_factor)
            new_height = int(30 * scaling_factor)

            original_image = Image.open('ico/donate.png')
            resized_image = original_image.resize((new_width, new_height), Image.LANCZOS)
            self.paypal_image = ImageTk.PhotoImage(resized_image)
        except FileNotFoundError:
            print("Warning: donate.png not found. Using default text button.")
            self.paypal_image = None

    def create_slider_grid(self, mainframe, starting_row):
        slider_frame = ttk.Frame(mainframe)
        slider_frame.grid(row=starting_row, column=0, columnspan=3, pady=10)
        
        for col in range(4):
            slider_frame.columnconfigure(col, weight=1)

        self.create_slider(slider_frame, "FFB Deadzone:", self.deadzone_value, 0, 0, from_=self.deadzone_min, to=self.deadzone_max)
        self.create_slider(slider_frame, "Max Output Force:", self.max_output_value, 1, 0, from_=self.max_output_min, to=self.max_output_max)
        self.create_slider(slider_frame, "Power Boost:", self.power_boost_value, 2, 0, from_=self.power_boost_min, to=self.power_boost_max)

    def update_status_label(self):
        """Update the status label with loaded preset, saved LUT, and compare LUT names."""
        status_parts = []
        if self.loaded_preset_name:
            modified_text = " (modified)" if self.is_preset_modified() else ""
            status_parts.append(f"Preset loaded: {self.loaded_preset_name}{modified_text}")
        if self.saved_lut_name:
            status_parts.append(f"LUT saved: {self.saved_lut_name}")
        if self.compare_lut_name:
            status_parts.append(f"Comparison LUT loaded: {self.compare_lut_name}")
        status_text = " | ".join(status_parts) if status_parts else "Adjust FFB Deadzone, Max Output Force, and Power Boost, then click Apply."
        self.status_label.config(text=status_text)

    def load_compare_lut(self):
        """Load and display a LUT file for comparison."""
        file_path = filedialog.askopenfilename(defaultextension=".lut", filetypes=[("LUT files", "*.lut"), ("All files", "*.*")])
        if file_path:
            self.compare_lut = Lut()
            with open(file_path, "r") as file:
                for line in file:
                    x, y = map(float, line.strip().split("|"))
                    self.compare_lut.addPoint(x, y)
            self.compare_lut_name = os.path.basename(file_path)
            self.compare_lut_modified = True
            self.apply_correction()

    def clear_comparison(self):
        """Clear the comparison LUT curve."""
        self.compare_lut = None
        self.compare_lut_name = None
        self.compare_lut_modified = False
        self.apply_correction()

    def update_combined_output(self):
        """Update the combined LUT output with both current and comparison LUTs."""
        self.combined_output.config(state=tk.NORMAL)
        self.combined_output.delete(1.0, tk.END)

        lut_points = {x: y for x, y in self.lut.points}
        compare_points = {x: y for x, y in self.compare_lut.points} if self.compare_lut else None

        combined_content = []
        first_compare_y = 0.0

        if compare_points:
            first_compare_y = compare_points.get(0.0, 0.0)
            combined_content.append(f"0.000|0.00000 - {first_compare_y:.5f}")
        else:
            combined_content.append("0.000|0.00000")
        
        previous_compare_y = first_compare_y
        for x in sorted(lut_points.keys()):
            if x == 0.000:
                continue  # Skip the first value
            current_y = lut_points[x]
            if compare_points:
                compare_y = compare_points.get(x, previous_compare_y)
                previous_compare_y = compare_y
                combined_content.append(f"{x:.3f}|{current_y:.5f} - {compare_y:.5f}")
            else:
                combined_content.append(f"{x:.3f}|{current_y:.5f}")
        
        self.combined_output.insert(tk.END, "\n".join(combined_content))
        self.combined_output.config(state=tk.DISABLED)

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
            self.saved_lut_name = os.path.basename(file_path)
            self.update_status_label()

    def load_preset(self):
        """Load slider values from a preset file."""
        file_path = filedialog.askopenfilename(initialdir="./presets", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if file_path:
            with open(file_path, "r") as file:
                preset = json.load(file)
                self.deadzone_value.set(preset["deadzone"])
                self.max_output_value.set(preset["max_output"])
                self.power_boost_value.set(preset["power_boost"])
                # Save initial values
                self.initial_deadzone_value = preset["deadzone"]
                self.initial_max_output_value = preset["max_output"]
                self.initial_power_boost_value = preset["power_boost"]
            self.loaded_preset_name = os.path.basename(file_path)
            self.apply_correction()

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
        """Show the help box."""
        help_popup = tk.Toplevel(self.root)
        help_popup.title("Help - Settings Descriptions")
        help_popup.iconbitmap(get_icon_path())
        max_text_width = 600

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
            setting_label = ttk.Label(frame, text=f"{setting}:", font=('TkDefaultFont', 10, 'bold'))
            setting_label.pack(anchor=tk.W, padx=20, pady=5)
            description_label = ttk.Label(frame, text=description, wraplength=max_text_width, justify=tk.LEFT, font=('TkDefaultFont', 10))
            description_label.pack(anchor=tk.W, padx=30)

        additional_info_frame = ttk.Frame(help_popup)
        additional_info_frame.pack(fill=tk.X, pady=(10,20))
    
        doc_text = "Refer to the documentation to learn how to use the LUT file in your simulator." 
        doc_label = ttk.Label(additional_info_frame, wraplength=max_text_width, text=doc_text, font=('TkDefaultFont', 10)) 
        doc_label.pack(anchor=tk.W, padx=20, pady=(5,10))

        version_label = ttk.Label(additional_info_frame, text="Current app version: " + self.version)
        version_label.pack(anchor=tk.W, padx=20, pady=(5,0))

        button_frame = ttk.Frame(help_popup)
        button_frame.pack(pady=(0, 30))

        git_link = "https://github.com/Luke460/force-feedback-manager"
        git_button = ttk.Button(button_frame, text="Visit GitHub Page", command=lambda: webbrowser.open(git_link))
        git_button.pack(side=tk.LEFT, padx=5)

        ufb_link = "https://github.com/Luke460/force-feedback-manager/discussions/2"
        ufb_button = ttk.Button(button_frame, text="User Feedback", command=lambda: webbrowser.open(ufb_link))
        ufb_button.pack(side=tk.LEFT, padx=5)

        rel_link = "https://github.com/Luke460/force-feedback-manager/releases"
        releases_button = ttk.Button(button_frame, text="Check Updates", command=lambda: webbrowser.open(rel_link))
        releases_button.pack(side=tk.LEFT, padx=5)

        self.center_popup(help_popup)

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

    def apply_correction(self, event=None):
        """Apply the deadzone and max output values to generate the LUT."""
        lut_size = 1000
        self.deadzone_value.set(limit_value(self.deadzone_value.get(), self.deadzone_min, self.deadzone_max))
        self.max_output_value.set(limit_value(self.max_output_value.get(), self.max_output_min, self.max_output_max))
        self.power_boost_value.set(limit_value(self.power_boost_value.get(), self.power_boost_min, self.power_boost_max))
        deadzone = self.deadzone_value.get()
        max_output = self.max_output_value.get()
        power_boost = self.power_boost_value.get()
        self.lut = generateCustomLut(lut_size, deadzone, max_output, power_boost)
        self.update_combined_output()
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
        
    def update_chart(self, compare_lut=None):
        """Update the chart with the current settings, optionally comparing with another LUT."""
        self.ax.clear()

        # Add default lut line
        self.ax.plot([0, 100], [0, 100], color='gray', linewidth=0.5, dashes=(2, 2))

        lut_size = 100
        deadzone = self.deadzone_value.get()
        max_output = self.max_output_value.get()
        power_boost = self.power_boost_value.get()
        
        lut = generateCustomLut(lut_size, deadzone, max_output, power_boost)
        x_vals = [x for x, y in lut.points]
        y_vals = [y for x, y in lut.points]
        
        self.ax.plot(x_vals, y_vals, label='Current LUT', color='blue', linewidth=2)
        
        # Find the intersection point of the LUT curve with the y-axis
        intersection_y = next((y for x, y in lut.points if x == 0), 0)

        # Ensure the comparison LUT is always plotted if it exists
        if self.compare_lut_modified and hasattr(self, 'compare_lut') and self.compare_lut:
            compare_x_vals = [x for x, y in self.compare_lut.points]
            compare_y_vals = [y for x, y in self.compare_lut.points]
            self.ax.plot(compare_x_vals, compare_y_vals, label='Comparison LUT', color='orange', linewidth=2)
        
        # Find the maximum y value of the LUT curve
        max_y = max(y_vals)
        
        # Add horizontal line for max output force if less than 100
        if max_output < 100.0:
            self.ax.axhline(max_y, color='forestgreen', linestyle='--', label='Max Output Force')
        
        # Add vertical line for clipping if max_output >= 100.0
        if max_output > 100.0:
            clipping_point = next((x for x, y in lut.points if y >= 1.0), 1.0)
            self.ax.axvline(clipping_point, color='red', linestyle='--', label='Clipping')

        # Add horizontal line for deadzone
        if deadzone > 0.0:
            self.ax.axhline(intersection_y, color='dimgrey', linestyle='--', label='Deadzone')

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

        self.update_status_label()
        
    def save_lut(self):
        """Save the LUT to a file."""
        self.apply_correction()
        
        lut_content = ["0.000|0.00000"]  # First value
        lut_content += [f"{x:.3f}|{y:.5f}" for x, y in self.lut.points if x != 0.000]

        file_path = filedialog.asksaveasfilename(defaultextension=".lut", filetypes=[("LUT files", "*.lut"), ("All files", "*.*")])
        if file_path:
            with open(file_path, "w") as file:
                file.write("\n".join(lut_content))
            self.saved_lut_name = os.path.basename(file_path)
            self.update_status_label()
            self.show_donation_popup()

    def load_compare_lut(self):
        """Load and display a LUT file for comparison."""
        file_path = filedialog.askopenfilename(defaultextension=".lut", filetypes=[("LUT files", "*.lut"), ("All files", "*.*")])
        if file_path:
            self.compare_lut = Lut()
            with open(file_path, "r") as file:
                for line in file:
                    x, y = map(float, line.strip().split("|"))
                    self.compare_lut.addPoint(x, y)
            self.compare_lut_name = os.path.basename(file_path)
            self.compare_lut_modified = True
            self.apply_correction()

    def is_preset_modified(self):
        """Check if the current preset values have been modified."""
        return (self.loaded_preset_name and (
            self.deadzone_value.get() != self.initial_deadzone_value or
            self.max_output_value.get() != self.initial_max_output_value or
            self.power_boost_value.get() != self.initial_power_boost_value))

    def show_donation_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Support Force Feedback Manager")
        popup.iconbitmap(get_icon_path())

        label = ttk.Label(popup, text="Thank you for using Force Feedback Manager!\nIf you would like to support my work, please consider making a donation <3", font=('TkDefaultFont', 11))
        label.pack(pady=20, padx=20)

        button_frame = ttk.Frame(popup)
        button_frame.pack(pady=(0,20), padx=10)

        link = "https://www.paypal.com/donate?hosted_button_id=WVSY5VX8TA4ZE";
        donate_button = self.create_donation_button(mainframe=button_frame, command=lambda: open_link(link))
        donate_button.pack(side=tk.LEFT, padx=5)

        self.center_popup(popup)

    def on_closing(self):
        """Handle the window closing event."""
        self.root.destroy()
        sys.exit()

if __name__ == "__main__":
    root = tb.Window(themename="superhero")
    app = ForceFeedbackManagerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
