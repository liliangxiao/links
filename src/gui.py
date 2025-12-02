#!/usr/bin/python3
"""
@file gui.py
@brief Graphical User Interface (GUI) for the Links Project.

This Python script provides an interactive GUI for managing, editing, and visualizing
links between modules and ports, using Tkinter. It interacts with the underlying
'links' command-line tool for core data manipulation and Graphviz for visualization.

@author Your Name/Organization (Replace with actual author)
@date 2025-12-02

@license MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import xml.etree.ElementTree as ET
from collections import OrderedDict
import subprocess
import os
import datetime
import tempfile

# Use a temporary directory for logging to avoid cluttering the project root
# and allow for potential cleanup.
# The actual path should ideally be dynamically determined or configurable.
# For this exercise, we'll use a placeholder.
# In a real application, consider appdirs or a user-defined setting.
temp_dir = os.path.join(tempfile.gettempdir(), "links_gui_logs")
os.makedirs(temp_dir, exist_ok=True)


def log_message(message):
    """
    Logs a timestamped message to a debug file within the temporary directory.
    Useful for debugging GUI interactions and subprocess calls.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(temp_dir, "debug.log"), "a") as f:
        f.write(f"[{timestamp}] {message}\n")

class ToolTip:
    """
    Provides a simple tooltip functionality for Tkinter widgets.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        """Displays the tooltip window."""
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True) # Remove window decorations
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        """Hides and destroys the tooltip window."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None


class LinkEditor(tk.Tk):
    """
    Main application window for the Link Editor GUI.
    Manages the display of links, interactions with the 'links' CLI,
    and visualization of the graph.
    """
    def __init__(self):
        super().__init__()
        self.title("Link Editor")
        self.geometry("1200x600")

        self.tree = None           # Treeview widget for displaying links
        self.links = []            # List of OrderedDicts representing link data
        self.xml_file = "links_data.xml" # Default XML data file
        self.port_map = {}         # Dictionary to map (module, port) to type for quick lookup
        self.next_link_id = 0      # Counter for assigning unique IDs to links for internal tracking

        self.create_widgets()
        self.load_links() # Initial load of links from XML

        self.create_graph_window() # Create a separate window for graph visualization
        self.refresh_graph()       # Generate and display the initial graph

    def create_graph_window(self):
        """
        Creates a Toplevel window to display the Graphviz-generated image.
        """
        self.graph_window = tk.Toplevel(self)
        self.graph_window.title("Link Graph")
        self.graph_window.geometry("800x600")

        # Canvas with scrollbars for the graph image
        canvas = tk.Canvas(self.graph_window)
        v_scrollbar = ttk.Scrollbar(self.graph_window, orient="vertical", command=canvas.yview)
        h_scrollbar = ttk.Scrollbar(self.graph_window, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)
        
        self.graph_canvas = canvas
        self.graph_image = None # Keep a reference to prevent garbage collection of the PhotoImage

    def refresh_graph(self):
        """
        Executes the 'links dot' command to generate graph files and displays
        the 'graph.png' in the graph_canvas.
        """
        log_message("--- refresh_graph started ---")
        try:
            # Execute the 'links dot' command to generate ./graph.dot, ./graph.png, ./graph.svg
            # Assumes 'links' executable is in the current working directory or PATH.
            # We explicitly output to ./graph.dot, so the shell command is just 'links dot'.
            log_message("Executing: ./links dot")
            result = subprocess.run(["./links", "dot"], check=True, capture_output=True, text=True, cwd="./")
            log_message(f"Command stdout: {result.stdout.strip()}")
            log_message(f"Command stderr: {result.stderr.strip()}")
            log_message("Graph generation command completed successfully.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            errmsg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
            log_message(f"Error generating graph: {errmsg}")
            messagebox.showerror("Error", f"Failed to generate graph. Make sure 'links' executable exists and Graphviz is installed.\n{errmsg}")
            return
           
        try:
            image_path = os.path.join(".", "graph.png")
            # Ensure the image file actually exists and is not empty before loading
            if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
                log_message(f"Error: {image_path} does not exist or is empty after generation.")
                messagebox.showerror("Error", f"Graph image ({image_path}) not found or is empty after generation.")
                return

            log_message(f"Loading {image_path} (size: {os.path.getsize(image_path)} bytes)")
            # Explicitly set to None to break potential Tkinter caching of the old image object
            self.graph_image = None 
            self.graph_image = tk.PhotoImage(file=image_path)
            self.graph_canvas.delete("all") # Clear previous image
            self.graph_canvas.create_image(0, 0, anchor="nw", image=self.graph_image)
            self.graph_canvas.config(scrollregion=self.graph_canvas.bbox("all")) # Adjust scroll region
            log_message("Graph image loaded and canvas updated.")
        except tk.TclError as e:
            log_message(f"Failed to load graph image: {e}")
            messagebox.showerror("Error", f"Failed to load graph image: {e}. Ensure the image file is valid.")
        log_message("--- refresh_graph finished ---")

    def create_widgets(self):
        """
        Initializes and arranges all main GUI widgets.
        """
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Treeview for displaying links
        columns = ("src_mod", "src_port", "src_type", "dst_mod", "dst_port", "dst_type")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings")
        
        headings = {
            "src_mod": "Source Module", "src_port": "Source Port", "src_type": "Source Type",
            "dst_mod": "Destination Module", "dst_port": "Destination Port", "dst_type": "Destination Type"
        }
        for col, heading in headings.items():
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=150)
            
        self.tree.pack(side="left", fill="both", expand=True)
        # Bind keyboard and mouse events
        self.tree.bind("<Delete>", lambda e: self.delete_link())
        self.tree.bind("<Double-1>", self.on_tree_double_click) # Bind double-click for in-place editing

        # Scrollbar for the Treeview
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Button frame for actions
        button_frame = ttk.Frame(self, padding=(0, 10))
        button_frame.pack(fill="x")

        # Add Link button with tooltip and keyboard binding
        add_button = ttk.Button(button_frame, text="Add Link", command=self.add_link)
        add_button.pack(side="left", padx=5)
        ToolTip(add_button, "Add a new link (Ctrl+A)")
        self.bind_all("<Control-a>", lambda e: self.add_link())
        
        # Delete Link button with tooltip
        delete_button = ttk.Button(button_frame, text="Delete Link", command=self.delete_link)
        delete_button.pack(side="left", padx=5)
        ToolTip(delete_button, "Delete selected link (Delete)")

        # Save (Refresh) button with tooltip and keyboard binding
        save_button = ttk.Button(button_frame, text="Refresh View (from XML)", command=self.save_links)
        save_button.pack(side="right", padx=5)
        ToolTip(save_button, "Reload all links from XML and refresh graph (Ctrl+S)")
        self.bind_all("<Control-s>", lambda e: self.save_links())

    def load_links(self):
        """
        Loads link data from the XML file ('links_data.xml') into the GUI's internal
        data structures and refreshes the Treeview display.
        """
        # Clear existing data in Treeview and internal lists
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.links.clear()
        self.port_map.clear()
        self.next_link_id = 0 # Reset unique ID counter for internal links tracking


        try:
            xml_tree = ET.parse(self.xml_file)
            root_element = xml_tree.getroot() # Get the root element of the XML
            
            # First pass: Populate port_map for destination type lookups
            for module_elem in root_element.findall("module"):
                module_name = module_elem.get("name")
                for port_elem in module_elem.findall("port"):
                    port_name = port_elem.get("name")
                    self.port_map[(module_name, port_name)] = port_elem.get("type")

            # Second pass: Extract links and populate the Treeview
            for module_elem in root_element.findall("module"):
                src_mod_name = module_elem.get("name")
                for port_elem in module_elem.findall("port"):
                    # A link exists if a port is 'out' and has dest_mod and dest_port attributes
                    if (port_elem.get("dir") == "out" and 
                        port_elem.get("dest_mod") and 
                        port_elem.get("dest_port")):
                        
                        link_data = OrderedDict([
                            ("src_mod", src_mod_name),
                            ("src_port", port_elem.get("name")),
                            ("src_type", port_elem.get("type")),
                            ("dst_mod", port_elem.get("dest_mod")),
                            ("dst_port", port_elem.get("dest_port")),
                            # Look up destination type using the populated port_map
                            ("dst_type", self.port_map.get((port_elem.get("dest_mod"), port_elem.get("dest_port")))),
                            ("unique_id", self.next_link_id) # Assign a unique ID for internal tracking
                        ])
                        self.links.append(link_data)
                        
                        # Insert into Treeview, using unique_id as the internal item identifier (iid)
                        new_iid = str(self.next_link_id)
                        self.tree.insert("", "end", values=list(link_data.values())[:6], iid=new_iid, tags=(new_iid,))
                        log_message(f"load_links: Added link unique_id={self.next_link_id}, Treeview iid={new_iid}, data={link_data}")
                        self.next_link_id += 1
        except (FileNotFoundError, ET.ParseError) as e:
            messagebox.showerror("Error", f"Failed to load {self.xml_file}. Ensure it's valid XML or empty.\n{e}")

    def add_link(self):
        """
        Adds a new link by prompting the user for source and destination,
        then calls the 'links add' CLI command and refreshes the GUI.
        If a link is selected, it pre-populates with data from the selected link.
        """
        log_message("--- add_link started ---")
        selected_item = self.tree.focus()

        initial_link_data = OrderedDict([
            ("src_mod", ""), ("src_port", ""), ("src_type", ""),
            ("dst_mod", ""), ("dst_port", ""), ("dst_type", ""), # dst_type will be derived
        ])

        # If an item is selected, pre-populate the new link with its data
        if selected_item:
            item_tags = self.tree.item(selected_item, 'tags')
            if item_tags:
                unique_id_from_item = item_tags[0]
                original_link_to_copy = next((link for link in self.links if str(link.get("unique_id")) == unique_id_from_item), None)
                
                if original_link_to_copy:
                    copied_link = original_link_to_copy.copy()
                    initial_link_data.update(copied_link)
                    initial_link_data["dst_type"] = "" # Clear derived dst_type
                    # Make the new link distinct to avoid immediate conflicts
                    initial_link_data["src_port"] = f"{initial_link_data['src_port']}_copy{self.next_link_id}"
                    log_message(f"Duplicating link from ID {unique_id_from_item}. New src_port: {initial_link_data['src_port']}")
                else:
                    log_message(f"Warning: Original link data for ID {unique_id_from_item} not found in self.links.")
            else:
                log_message(f"Warning: Selected Treeview item {selected_item} has no unique ID tags.")

        # Prompt for source (Module::Port:Type)
        src_input = simpledialog.askstring("Add Link", "Enter Source (Module::Port:Type):", initialvalue=f"{initial_link_data['src_mod']}::{initial_link_data['src_port']}:{initial_link_data['src_type']}")
        if not src_input: return # User cancelled

        # Prompt for destination (Module::Port)
        dst_input = simpledialog.askstring("Add Link", "Enter Destination (Module::Port):", initialvalue=f"{initial_link_data['dst_mod']}::{initial_link_data['dst_port']}")
        if not dst_input: return # User cancelled

        try:
            # Execute the 'links add' command
            log_message(f"Executing links add command: ./links add \"{src_input}\" \"{dst_input}\"")
            result = subprocess.run(["./links", "add", src_input, dst_input], check=True, capture_output=True, text=True)
            log_message(f"links add stdout: {result.stdout.strip()}")
            log_message(f"links add stderr: {result.stderr.strip()}")
            
            if result.returncode == 0:
                messagebox.showinfo("Success", "Link added successfully.")
            else:
                raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout, stderr=result.stderr)

            # After adding, reload data and refresh graph
            self.load_links()
            self.refresh_graph()

            # Attempt to select the newly added link for immediate editing
            # This assumes the newly added link will be the last one in the self.links list
            if self.links:
                newly_added_link_unique_id = str(self.links[-1]["unique_id"])
                re_identified_item_id = next((child_iid for child_iid in self.tree.get_children() 
                                              if newly_added_link_unique_id in self.tree.item(child_iid, 'tags')), None)
                if re_identified_item_id:
                    self.tree.see(re_identified_item_id)
                    self.tree.selection_set(re_identified_item_id)
                    self.tree.focus(re_identified_item_id)
                    
                    # Optionally trigger in-place edit for the first column
                    bbox_first_col = self.tree.bbox(re_identified_item_id, "#1")
                    if bbox_first_col:
                        event_mock = type('Event', (object,), {'x': bbox_first_col[0] + 5, 'y': bbox_first_col[1] + 5})()
                        self.on_tree_double_click(event_mock)
                else:
                    log_message(f"Could not re-identify newly added item with unique_id: {newly_added_link_unique_id}")

        except subprocess.CalledProcessError as e:
            errmsg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
            log_message(f"Error adding link: {errmsg}")
            messagebox.showerror("Error", f"Failed to add link:\n{errmsg}")
        except Exception as e:
            log_message(f"An unexpected error occurred in add_link: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        
        log_message("--- add_link finished ---")


    def delete_link(self):
        """
        Deletes the currently selected link in the Treeview.
        Calls the 'links remove' CLI command and refreshes the GUI.
        """
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a link to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this link?"):
            item_tags = self.tree.item(selected_item, 'tags')
            if not item_tags:
                messagebox.showerror("Error", "Internal error: Selected link item has no ID.")
                return

            unique_id_from_item = item_tags[0] # The first tag is our unique_id
            
            link_to_delete = next((link for link in self.links if str(link.get("unique_id")) == unique_id_from_item), None)
            
            if link_to_delete is None:
                messagebox.showerror("Error", "Link data for selected item not found. Data might be out of sync. Please reload.")
                return

            try:
                # Construct arguments for the './links remove' command
                src_str = f"{link_to_delete['src_mod']}::{link_to_delete['src_port']}:{link_to_delete['src_type']}"
                dst_str = f"{link_to_delete['dst_mod']}::{link_to_delete['dst_port']}"

                log_message(f"Executing links remove command: ./links remove \"{src_str}\" \"{dst_str}\"")
                result = subprocess.run(["./links", "remove", src_str, dst_str], check=True, capture_output=True, text=True)
                log_message(f"links remove stdout: {result.stdout.strip()}")
                log_message(f"links remove stderr: {result.stderr.strip()}")

                if result.returncode == 0:
                    messagebox.showinfo("Success", "Link deleted successfully.")
                else:
                    raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout, stderr=result.stderr)
                
                # After deletion, reload data and refresh graph
                self.load_links()
                self.refresh_graph()
            except subprocess.CalledProcessError as e:
                errmsg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
                log_message(f"Error deleting link: {errmsg}")
                messagebox.showerror("Error", f"Failed to delete link:\n{errmsg}")
            except Exception as e:
                log_message(f"An unexpected error occurred in delete_link: {e}")
                messagebox.showerror("Error", f"An unexpected error occurred: {e}")


    def save_links(self):
        """
        This method is now used to refresh the GUI's view by reloading data from
        links_data.xml and regenerating the graph. It effectively "saves" changes
        made via the CLI by refreshing the view of the persistent data.
        """
        log_message("--- save_links (refreshing view) started ---")
        try:
            self.load_links() # Reloads from XML
            self.refresh_graph() # Regenerates and displays graph
            messagebox.showinfo("Info", "View refreshed from links_data.xml.")
        except Exception as e:
            log_message(f"Error refreshing view on save: {e}")
            messagebox.showerror("Error", f"Failed to refresh view from XML: {e}")
        log_message("--- save_links (refreshing view) finished ---")

    def on_tree_double_click(self, event):
        """
        Handles double-click events on the Treeview to enable in-place editing
        of certain link properties.
        """
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)

        # Map Treeview's internal column identifier (#0, #1, etc.) to actual column name.
        # Skip editing 'dst_type' as it's a derived property.
        if column == "#6": # dst_type column
            messagebox.showinfo("Info", "Destination type is derived and cannot be directly edited.")
            return

        col_index = int(column.replace('#', '')) - 1 # Adjust for #0 being the hidden column
        if col_index < 0: # This means it's the #0 column (tree column), which is not editable
            return
        
        column_name = self.tree["columns"][col_index]

        bbox = self.tree.bbox(item, column)
        if bbox is None:
            return

        current_value = self.tree.item(item, 'values')[col_index]

        # Create an Entry widget for in-place editing
        entry_edit = ttk.Entry(self.tree)
        entry_edit.insert(0, current_value)
        entry_edit.select_range(0, tk.END) # Select all text
        entry_edit.focus_set()

        # Position the entry widget over the cell
        entry_edit.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])

        def _save_edit(event=None):
            """
            Saves the edited value back to the underlying data using CLI commands.
            """
            new_value = entry_edit.get()
            
            try:
                item_tags = self.tree.item(item, 'tags')
                if not item_tags:
                    log_message(f"Error: Treeview item {item} has no tags. Cannot find unique_id.")
                    messagebox.showerror("Error", "Internal error: Link item has no ID. Please reload.")
                    return

                unique_id_from_item = item_tags[0]
                link_to_edit = next((link for link in self.links if str(link.get("unique_id")) == unique_id_from_item), None)
                
                if link_to_edit is None:
                    messagebox.showerror("Error", "Link data for selected item not found. Data might be out of sync. Please reload.")
                    return
                
                # --- Handle specific column edits ---
                if column_name == "src_type":
                    old_src_type = link_to_edit['src_type']
                    if new_value != old_src_type:
                        src_mod = link_to_edit['src_mod']
                        src_port = link_to_edit['src_port']
                        
                        # Use 'links edit' command for source type change
                        # Assume 'out' direction for source ports in this context
                        cmd = ["./links", "edit", f"{src_mod}::{src_port}", new_value, "out"] 
                        log_message(f"Executing links edit command: {' '.join(cmd)}")
                        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                        log_message(f"links edit stdout: {result.stdout.strip()}")
                        log_message(f"links edit stderr: {result.stderr.strip()}")
                        
                        if result.returncode == 0:
                            messagebox.showinfo("Success", "Source type updated successfully.")
                            self.load_links()
                            self.refresh_graph()
                        else:
                            raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout, stderr=result.stderr)
                    else:
                        log_message(f"No change in src_type for {link_to_edit['src_mod']}::{link_to_edit['src_port']}. No action.")
                
                elif column_name in ["src_mod", "src_port", "dst_mod", "dst_port"]:
                    if new_value != current_value:
                        # For changes to module/port names, we need to remove the old link and add a new one.
                        src_str_old = f"{link_to_edit['src_mod']}::{link_to_edit['src_port']}:{link_to_edit['src_type']}"
                        dst_str_old = f"{link_to_edit['dst_mod']}::{link_to_edit['dst_port']}"
                        
                        # Create a temporary dictionary with the updated value for constructing new link command
                        updated_link_temp = link_to_edit.copy()
                        updated_link_temp[column_name] = new_value

                        src_str_new = f"{updated_link_temp['src_mod']}::{updated_link_temp['src_port']}:{updated_link_temp['src_type']}"
                        dst_str_new = f"{updated_link_temp['dst_mod']}::{updated_link_temp['dst_port']}"

                        # Execute remove and add commands via subprocess
                        remove_cmd = ["./links", "remove", src_str_old, dst_str_old]
                        log_message(f"Executing links remove command (for in-place edit): {' '.join(remove_cmd)}")
                        subprocess.run(remove_cmd, check=True, capture_output=True, text=True) # Check for errors not strictly necessary here, add will indicate if failed to remove

                        add_cmd = ["./links", "add", src_str_new, dst_str_new]
                        log_message(f"Executing links add command (for in-place edit): {' '.join(add_cmd)}")
                        subprocess.run(add_cmd, check=True, capture_output=True, text=True)
                        
                        messagebox.showinfo("Success", f"{column_name.replace('_', ' ').title()} updated successfully.")
                        self.load_links()
                        self.refresh_graph()
                        
                        # --- Re-selection logic ---
                        # Try to find and re-select the modified link after reload
                        re_selected = False
                        found_unique_id = None
                        for link_dict_after_load in self.links:
                            match = True
                            # Compare relevant fields to identify the modified link
                            for key_to_compare in ["src_mod", "src_port", "src_type", "dst_mod", "dst_port"]:
                                if link_dict_after_load.get(key_to_compare) != updated_link_temp.get(key_to_compare):
                                    match = False
                                    break
                            if match:
                                found_unique_id = str(link_dict_after_load["unique_id"])
                                break
                        
                        if found_unique_id:
                            re_identified_item_id = next((child_iid for child_iid in self.tree.get_children() 
                                                          if found_unique_id in self.tree.item(child_iid, 'tags')), None)
                            if re_identified_item_id:
                                self.tree.see(re_identified_item_id)
                                self.tree.selection_set(re_identified_item_id)
                                self.tree.focus(re_identified_item_id)
                                re_selected = True
                                log_message(f"Re-selected item: {re_identified_item_id} with unique_id: {found_unique_id}")
                        
                        if not re_selected:
                            log_message("Failed to re-select item after in-place edit.")
                        # --- End re-selection logic ---

                    else:
                        log_message(f"No change in {column_name} for {link_to_edit['src_mod']}::{link_to_edit['src_port']}. No action.")
                
                else:
                    log_message(f"Attempted to edit unsupported column {column_name} via direct cell edit. No action.")

            except subprocess.CalledProcessError as e:
                errmsg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
                log_message(f"Error during in-place edit CLI command: {errmsg}")
                messagebox.showerror("Error", f"Failed to save in-place edit:\n{errmsg}")
            except Exception as e:
                log_message(f"An unexpected error occurred in _save_edit: {e}")
                messagebox.showerror("Error", f"Failed to save edit: {e}")
            finally:
                entry_edit.destroy() # Always destroy the entry widget
                self.tree.focus_set() # Return focus to treeview
            log_message("--- _save_edit finished ---")

        # Bind Enter key and focus loss to the save function
        entry_edit.bind("<Return>", _save_edit)
        entry_edit.bind("<FocusOut>", _save_edit)

if __name__ == "__main__":
    app = LinkEditor()
    app.mainloop()

