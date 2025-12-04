import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import xml.etree.ElementTree as ET
from collections import OrderedDict
import subprocess
import os
import datetime
import tempfile

temp_dir = "/home/ryder/.gemini/tmp/624f5738677a0804a93db48b0564719580210bf3caad456a7dc2520d76d651ce"

def log_message(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(temp_dir, "debug.log"), "a") as f:
        f.write(f"[{timestamp}] {message}\n")

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None



class LinkEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Link Editor")
        self.geometry("1200x600")

        self.tree = None
        self.links = []
        self.xml_file = "links_data.xml"
        self.port_map = {}

        self.create_widgets()
        self.load_links()

        self.create_graph_window()
        self.refresh_graph()

    def create_graph_window(self):
        self.graph_window = tk.Toplevel(self)
        self.graph_window.title("Link Graph")
        self.graph_window.geometry("800x600")

        canvas = tk.Canvas(self.graph_window)
        v_scrollbar = ttk.Scrollbar(self.graph_window, orient="vertical", command=canvas.yview)
        h_scrollbar = ttk.Scrollbar(self.graph_window, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)
        
        self.graph_canvas = canvas
        self.graph_image = None # Keep a reference

    def refresh_graph(self):
        log_message("--- refresh_graph started ---")
        try:
            log_message("Executing: ./links dot")
            result = subprocess.run(["./links", "dot"], check=True, capture_output=True, text=True)
            log_message(f"Command stdout: {result.stdout.strip()}")
            log_message(f"Command stderr: {result.stderr.strip()}")
            log_message("Graph generation command completed successfully.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            errmsg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
            log_message(f"Error generating graph: {errmsg}")
            messagebox.showerror("Error", f"Failed to generate graph:\n{errmsg}")
            return
           
        try:
            # Ensure the image file actually exists and is not empty before loading
            if not os.path.exists("graph.png") or os.path.getsize("graph.png") == 0:
                log_message("Error: graph.png does not exist or is empty after generation.")
                messagebox.showerror("Error", "Graph image (graph.png) not found or is empty.")
                return

            log_message(f"Loading graph.png (size: {os.path.getsize('graph.png')} bytes)")
            # Explicitly set to None to break potential Tkinter caching of the old image object
            self.graph_image = None
            self.graph_image = tk.PhotoImage(file="graph.png")
            self.graph_canvas.delete("all")
            self.graph_canvas.create_image(0, 0, anchor="nw", image=self.graph_image)
            self.graph_canvas.config(scrollregion=self.graph_canvas.bbox("all"))
            log_message("Graph image loaded and canvas updated.")
        except tk.TclError as e:
            log_message(f"Failed to load graph image: {e}")
            messagebox.showerror("Error", f"Failed to load graph image: {e}")
        log_message("--- refresh_graph finished ---")

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Treeview
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
        self.tree.bind("<Delete>", lambda e: self.delete_link())
        self.tree.bind("<Double-1>", self.on_tree_double_click) # Bind double-click for in-place editing

        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Button frame
        button_frame = ttk.Frame(self, padding=(0, 10))
        button_frame.pack(fill="x")

        add_button = ttk.Button(button_frame, text="Add Link", command=self.add_link)
        add_button.pack(side="left", padx=5)
        ToolTip(add_button, "Add a new link (Ctrl+A)")
        self.bind_all("<Control-a>", lambda e: self.add_link())


        
        delete_button = ttk.Button(button_frame, text="Delete Link", command=self.delete_link)
        delete_button.pack(side="left", padx=5)
        ToolTip(delete_button, "Delete selected link (Delete)")

        save_button = ttk.Button(button_frame, text="Save", command=self.save_links)
        save_button.pack(side="right", padx=5)
        ToolTip(save_button, "Save all changes (Ctrl+S)")
        self.bind_all("<Control-s>", lambda e: self.save_links())

    def load_links(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.links.clear()
        self.port_map.clear()
        self.next_link_id = 0 # Initialize unique ID counter


        try:
            xml_tree = ET.parse(self.xml_file)
            self.complete_xml_root = xml_tree.getroot() # Store the complete XML root
            root = self.complete_xml_root # Use this root for populating links

            for module in root.findall("module"):
                module_name = module.get("name")
                for port in module.findall("port"):
                    port_name = port.get("name")
                    self.port_map[(module_name, port_name)] = port.get("type")

            for module in root.findall("module"):
                src_mod_name = module.get("name")
                for port in module.findall("port"):
                    if port.get("dir") == "out" and port.get("dest_mod") and port.get("dest_port"):
                        link_data = OrderedDict([
                            ("src_mod", src_mod_name),
                            ("src_port", port.get("name")),
                            ("src_type", port.get("type")),
                            ("dst_mod", port.get("dest_mod")),
                            ("dst_port", port.get("dest_port")),
                            ("dst_type", self.port_map.get((port.get("dest_mod"), port.get("dest_port")))),
                            ("unique_id", self.next_link_id) # Assign unique ID
                        ])
                        self.links.append(link_data)
                        new_iid = str(self.next_link_id)
                        self.tree.insert("", "end", values=list(link_data.values())[:6], iid=new_iid, tags=(new_iid,))
                        log_message(f"load_links: Added link unique_id={self.next_link_id}, Treeview iid={new_iid}, data={link_data}")
                        self.next_link_id += 1
        except (FileNotFoundError, ET.ParseError) as e:
            messagebox.showerror("Error", f"Failed to load {self.xml_file}: {e}")

    def add_link(self):
        log_message("--- add_link started ---")
        selected_item = self.tree.focus()
        log_message(f"selected_item: {selected_item}")

        initial_link_data = OrderedDict([
            ("src_mod", ""),
            ("src_port", ""),
            ("src_type", ""),
            ("dst_mod", ""),
            ("dst_port", ""),
            ("dst_type", ""),
        ])

        if selected_item:
            # Retrieve the unique_id from the Treeview item's tags
            item_tags = self.tree.item(selected_item, 'tags')
            if not item_tags:
                log_message(f"Error: Selected Treeview item {selected_item} has no tags. Cannot duplicate.")
                messagebox.showerror("Error", "Internal error: Selected link item has no ID for duplication.")
                # Proceed with empty initial_link_data if ID is missing
            else:
                unique_id_from_item = item_tags[0] # Assuming the first tag is the unique_id
                
                # Find the link_data in self.links using the unique_id
                original_link_to_copy = None
                for link_dict in self.links:
                    if str(link_dict.get("unique_id")) == unique_id_from_item:
                        original_link_to_copy = link_dict
                        break
                
                if original_link_to_copy is None:
                    log_message(f"Error: Could not find original link with unique_id {unique_id_from_item} in self.links for duplication.")
                    messagebox.showerror("Error", "Original link data not found for duplication. Data might be out of sync. Please reload.")
                    # Proceed with empty initial_link_data if original is missing
                else:
                    copied_link = original_link_to_copy.copy()
                    log_message(f"copied_link: {copied_link}")
                    
                    # Update initial data with copied values
                    initial_link_data.update(copied_link)
                    # Clear dst_type as it's usually derived
                    initial_link_data["dst_type"] = ""
                    # Make the new link distinct by modifying its source port
                    initial_link_data["src_port"] = f"{initial_link_data['src_port']}_copy{self.next_link_id}"

        
        try:
            # Construct src and dst arguments for the ./links command
            # Source format: Module::Port:Type
            src_str = f"{initial_link_data['src_mod']}::{initial_link_data['src_port']}:{initial_link_data['src_type']}"
            # Destination format: Module::Port (type is optional for destination in 'links add' command)
            dst_str = f"{initial_link_data['dst_mod']}::{initial_link_data['dst_port']}"

            log_message(f"Executing links add command: ./links add \"{src_str}\" \"{dst_str}\"")
            result = subprocess.run(["./links", "add", src_str, dst_str], check=True, capture_output=True, text=True)
            log_message(f"links add stdout: {result.stdout.strip()}")
            log_message(f"links add stderr: {result.stderr.strip()}")
            
            if result.returncode == 0:
                messagebox.showinfo("Success", "Link added successfully.")
            else:
                raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout, stderr=result.stderr)

            # After adding via external command, reload links and refresh graph
            # The newly added link's unique_id will be re-assigned during load_links()
            self.load_links()
            self.refresh_graph()

            # The selection logic after save_links() should now correctly find the newly added item.
            # It will be the one with the src_port containing _copyX and the latest unique_id.

        except subprocess.CalledProcessError as e:
            errmsg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
            log_message(f"Error adding link: {errmsg}")
            messagebox.showerror("Error", f"Failed to add link:\n{errmsg}")
        
        log_message(f"initial_link_data after update: {initial_link_data}") # Keep for debugging previous state

        # The following block is the new selection logic, already correctly logging.
        # It needs to be outside the try-except to execute even if initial_link_data construction fails.

        # Save and refresh the entire structure. This will rebuild self.links and self.tree
        # and assign new, correct iids for all items.
        # self.save_links() # No longer needed here, add_link directly calls load_links/refresh_graph

        # After save_links(), the Treeview is reloaded. We need to find the newly added item.
        # The new item will be the last one in the tree, or we can look for it by content.
        # A simpler way is to re-select the last added link (which would be at index len(self.links)-1)
        # assuming no other changes occurred in between which might reorder self.links.
        # This implicitly assumes that the order is preserved, which load_links does.
        if len(self.links) > 0:
            # Find the item in the treeview that corresponds to the newly added link's unique_id
            # The newly added link should be the last one in self.links after save_links() reloads.
            newly_added_link_unique_id = str(self.links[-1]["unique_id"])
            log_message(f"add_link selection: Targeting newly_added_link_unique_id={newly_added_link_unique_id}")
            re_identified_item_id = ""
            for child_item_id in self.tree.get_children():
                item_tags_for_child = self.tree.item(child_item_id, 'tags')
                log_message(f"add_link selection: Checking child_item_id={child_item_id}, tags={item_tags_for_child}")
                if newly_added_link_unique_id in item_tags_for_child:
                    re_identified_item_id = child_item_id
                    log_message(f"add_link selection: Matched re_identified_item_id={re_identified_item_id}")
                    break

            if re_identified_item_id:
                # Scroll to and select the new item
                self.tree.see(re_identified_item_id)
                self.tree.selection_set(re_identified_item_id)
                self.tree.focus(re_identified_item_id)
                log_message(f"add_link selection: Successfully selected and focused on {re_identified_item_id}")

                # Trigger in-place edit for the first column of the new row
                bbox_first_col = self.tree.bbox(re_identified_item_id, "#1")
                if bbox_first_col:
                    x_coord = bbox_first_col[0] + 5
                    y_coord = bbox_first_col[1] + 5
                    event = type('Event', (object,), {'x': x_coord, 'y': y_coord})()
                    self.on_tree_double_click(event)
            else:
                log_message(f"Could not re-identify newly added item with unique_id: {newly_added_link_unique_id}")

        log_message("--- add_link finished ---")



    def delete_link(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a link to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this link?"):
            item_tags = self.tree.item(selected_item, 'tags')
            if not item_tags:
                messagebox.showerror("Error", "Internal error: Selected link item has no ID.")
                return

            unique_id_from_item = item_tags[0]
            
            link_to_delete = None
            for link_dict in self.links:
                if str(link_dict.get("unique_id")) == unique_id_from_item:
                    link_to_delete = link_dict
                    break
            
            if link_to_delete is None:
                messagebox.showerror("Error", "Link data for selected item not found. Data might be out of sync. Please reload.")
                return

            try:
                # Construct src and dst arguments for the ./links remove command
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
                
                self.load_links()
                self.refresh_graph()
            except subprocess.CalledProcessError as e:
                errmsg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
                log_message(f"Error deleting link: {errmsg}")
                messagebox.showerror("Error", f"Failed to delete link:\n{errmsg}")



    def save_links(self):
        log_message("--- save_links started (refreshing from XML) ---")
        try:
            self.load_links() 
            self.refresh_graph()
            messagebox.showinfo("Info", "View refreshed from links_data.xml.")
        except Exception as e:
            log_message(f"Error refreshing view on save: {e}")
            messagebox.showerror("Error", f"Failed to refresh view from XML: {e}")
        log_message("--- save_links finished ---")

    def on_tree_double_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)

        # Map Treeview's internal column identifier (#0, #1, etc.) to actual column name
        # The column names are: "src_mod", "src_port", "src_type", "dst_mod", "dst_port", "dst_type"
        # Skip editing 'dst_type' as it's derived
        if column == "#6": # dst_type column
            return

        col_index = int(column.replace('#', '')) - 1 # Adjust for #0 being the hidden column
        if col_index < 0: # This means it's the #0 column, which is not editable
            return
        
        column_name = self.tree["columns"][col_index]

        bbox = self.tree.bbox(item, column)
        if bbox is None:
            return

        # Get current value
        current_value = self.tree.item(item, 'values')[col_index]

        # Create entry widget
        entry_edit = ttk.Entry(self.tree)
        entry_edit.insert(0, current_value)
        entry_edit.select_range(0, tk.END)
        entry_edit.focus_set()

        # Place entry widget
        entry_edit.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])

        def _save_edit(event=None):
            new_value = entry_edit.get()
            
            # Update the underlying data (self.links)
            try:
                # Retrieve the unique_id from the Treeview item's tags
                item_tags = self.tree.item(item, 'tags')
                if not item_tags:
                    log_message(f"Error: Treeview item {item} has no tags. Cannot find unique_id.")
                    messagebox.showerror("Error", "Internal error: Link item has no ID. Please reload.")
                    entry_edit.destroy()
                    self.tree.focus_set()
                    return

                unique_id_from_item = item_tags[0]
                
                link_to_edit = None
                for link_dict in self.links:
                    if str(link_dict.get("unique_id")) == unique_id_from_item:
                        link_to_edit = link_dict
                        break
                
                if link_to_edit is None:
                    messagebox.showerror("Error", "Link data for selected item not found. Data might be out of sync. Please reload.")
                    entry_edit.destroy()
                    self.tree.focus_set()
                    return
                
                # --- New logic for _save_edit to use external links command ---
                if column_name == "src_type":
                    old_src_type = link_to_edit['src_type']
                    if new_value != old_src_type:
                        src_mod = link_to_edit['src_mod']
                        src_port = link_to_edit['src_port']
                        
                        cmd = ["./links", "edit", f"{src_mod}::{src_port}", new_value, "out"] # Assume 'out' direction for src_type
                        log_message(f"Executing links edit command: {' '.join(cmd)}")
                        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                        log_message(f"links edit stdout: {result.stdout.strip()}")
                        log_message(f"links edit stderr: {result.stderr.strip()}")
                        
                        if result.returncode == 0:
                            messagebox.showinfo("Success", "Source type updated successfully.")
                            # After editing, reload links and refresh graph
                            self.load_links()
                            self.refresh_graph()
                        else:
                            raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout, stderr=result.stderr)
                    else:
                        log_message(f"No change in src_type for {link_to_edit['src_mod']}::{link_to_edit['src_port']}. No action.")
                elif column_name in ["src_mod", "src_port", "dst_mod", "dst_port"]:
                    if new_value != current_value:
                        # Store old link details for removal
                        src_str_old = f"{link_to_edit['src_mod']}::{link_to_edit['src_port']}:{link_to_edit['src_type']}"
                        dst_str_old = f"{link_to_edit['dst_mod']}::{link_to_edit['dst_port']}"
                        
                        # Create a temporary dictionary for the new link data
                        # This ensures src_type is always included for 'add' command
                        updated_link_temp = link_to_edit.copy()
                        updated_link_temp[column_name] = new_value

                        # Construct new link details for adding
                        src_str_new = f"{updated_link_temp['src_mod']}::{updated_link_temp['src_port']}:{updated_link_temp['src_type']}"
                        dst_str_new = f"{updated_link_temp['dst_mod']}::{updated_link_temp['dst_port']}"

                        # Execute remove and add commands
                        remove_cmd = ["./links", "remove", src_str_old, dst_str_old]
                        log_message(f"Executing links remove command (for in-place edit): {' '.join(remove_cmd)}")
                        subprocess.run(remove_cmd, check=True, capture_output=True, text=True)

                        add_cmd = ["./links", "add", src_str_new, dst_str_new]
                        log_message(f"Executing links add command (for in-place edit): {' '.join(add_cmd)}")
                        subprocess.run(add_cmd, check=True, capture_output=True, text=True)
                        
                        messagebox.showinfo("Success", f"{column_name.replace('_', ' ').title()} updated successfully.")
                        self.load_links()
                        self.refresh_graph()
                        # Store expected_new_link for re-selection (next TODO)
                        self.expected_new_link_data = updated_link_temp.copy()
                        # Remove unique_id, xml_port_element as they will be re-assigned
                        self.expected_new_link_data.pop("unique_id", None)
                        
                        # --- Re-selection logic ---
                        re_selected = False
                        if hasattr(self, 'expected_new_link_data') and self.expected_new_link_data:
                            found_unique_id = None
                            for link_dict_after_load in self.links:
                                match = True
                                for key in ["src_mod", "src_port", "src_type", "dst_mod", "dst_port"]:
                                    if link_dict_after_load.get(key) != self.expected_new_link_data.get(key):
                                        match = False
                                        break
                                if match:
                                    found_unique_id = str(link_dict_after_load["unique_id"])
                                    break
                            
                            if found_unique_id:
                                re_identified_item_id = ""
                                for child_item_id in self.tree.get_children():
                                    item_tags_for_child = self.tree.item(child_item_id, 'tags')
                                    if found_unique_id in item_tags_for_child:
                                        re_identified_item_id = child_item_id
                                        break
                                if re_identified_item_id:
                                    self.tree.see(re_identified_item_id)
                                    self.tree.selection_set(re_identified_item_id)
                                    self.tree.focus(re_identified_item_id)
                                    re_selected = True
                                    log_message(f"Re-selected item: {re_identified_item_id} with unique_id: {found_unique_id}")
                            
                            del self.expected_new_link_data # Clear after use
                        
                        if not re_selected:
                            log_message("Failed to re-select item after in-place edit.")
                        # --- End re-selection logic ---

                    else:
                        log_message(f"No change in {column_name} for {link_to_edit['src_mod']}::{link_to_edit['src_port']}. No action.")
                elif column_name == "dst_type":
                    messagebox.showinfo("Info", "Destination type is derived and cannot be directly edited.")
                    log_message(f"Attempted to edit derived dst_type. Not allowed via direct cell edit.")
                else:
                    log_message(f"Attempted to edit unsupported column {column_name} via direct cell edit. No action.")


                entry_edit.destroy()
                self.tree.focus_set() # Return focus to treeview
                
            except subprocess.CalledProcessError as e:
                errmsg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
                log_message(f"Error during in-place edit: {errmsg}")
                messagebox.showerror("Error", f"Failed to save in-place edit:\n{errmsg}")
                entry_edit.destroy()
                self.tree.focus_set()
            except Exception as e:
                log_message(f"An unexpected error occurred in _save_edit: {e}")
                messagebox.showerror("Error", f"Failed to save edit: {e}")
                entry_edit.destroy()
                self.tree.focus_set()
            log_message("--- _save_edit finished ---")

        entry_edit.bind("<Return>", _save_edit)
        entry_edit.bind("<FocusOut>", _save_edit) # Save on focus loss

if __name__ == "__main__":
    app = LinkEditor()
    app.mainloop()
