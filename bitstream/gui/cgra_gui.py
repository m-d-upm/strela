import tkinter as tk
import tkinter.ttk as ttk
from PIL import Image, ImageTk
import argparse

from ProcessingElement import CGRA

# -----------------------------
# Image loading (kept as-is)
# -----------------------------
pe_base = Image.open("images/pe_bound.png").convert("RGBA")
img_north_in = Image.open("images/pe_n.png").convert("RGBA")
img_east_in = Image.open("images/pe_e.png").convert("RGBA")
img_south_in = Image.open("images/pe_s.png").convert("RGBA")
img_west_in = Image.open("images/pe_w.png").convert("RGBA")
img_fu = Image.open("images/pe_fu.png").convert("RGBA")
img_fu_n = Image.open("images/pe_fu_n.png").convert("RGBA")
img_fu_e = Image.open("images/pe_fu_e.png").convert("RGBA")
img_fu_s = Image.open("images/pe_fu_s.png").convert("RGBA")
img_fu_w = Image.open("images/pe_fu_w.png").convert("RGBA")

# North route images
img_north_1 = Image.open("images/pe_n_1.png").convert("RGBA")
img_north_2 = Image.open("images/pe_n_2.png").convert("RGBA")
img_north_3 = Image.open("images/pe_n_3.png").convert("RGBA")
img_north_4 = Image.open("images/pe_n_4.png").convert("RGBA")

north_dest_order = ["west", "south", "east", "fu_in1", "fu_in2", "fu_cin"]
north_dest_images = {
    "west": img_north_1,
    "south": img_north_2,
    "east": img_north_4,
    "fu_in1": img_north_3,
    "fu_in2": img_north_3,
    "fu_cin": img_north_3
}

# East route images
img_east_1 = Image.open("images/pe_e_1.png").convert("RGBA")
img_east_2 = Image.open("images/pe_e_2.png").convert("RGBA")
img_east_3 = Image.open("images/pe_e_3.png").convert("RGBA")
img_east_4 = Image.open("images/pe_e_4.png").convert("RGBA")

east_dest_order = ["west", "south", "north", "fu_in1", "fu_in2", "fu_cin"]
east_dest_images = {
    "west": img_east_2,
    "south": img_east_4,
    "north": img_east_1,
    "fu_in1": img_east_3,
    "fu_in2": img_east_3,
    "fu_cin": img_east_3
}

# South route images
img_south_1 = Image.open("images/pe_s_1.png").convert("RGBA")
img_south_2 = Image.open("images/pe_s_2.png").convert("RGBA")
img_south_3 = Image.open("images/pe_s_3.png").convert("RGBA")
img_south_4 = Image.open("images/pe_s_4.png").convert("RGBA")

south_dest_order = ["west", "east", "north", "fu_in1", "fu_in2", "fu_cin"]
south_dest_images = {
    "west": img_south_4,
    "east": img_south_1,
    "north": img_south_2,
    "fu_in1": img_south_3,
    "fu_in2": img_south_3,
    "fu_cin": img_south_3
}

# West route images
img_west_1 = Image.open("images/pe_w_1.png").convert("RGBA")
img_west_2 = Image.open("images/pe_w_2.png").convert("RGBA")
img_west_3 = Image.open("images/pe_w_3.png").convert("RGBA")
img_west_4 = Image.open("images/pe_w_4.png").convert("RGBA")

west_dest_order = ["south", "east", "north", "fu_in1", "fu_in2", "fu_cin"]
west_dest_images = {
    "south": img_west_1,
    "east": img_west_2,
    "north": img_west_4,
    "fu_in1": img_west_3,
    "fu_in2": img_west_3,
    "fu_cin": img_west_3
}

# GUI option lists
fu_operations = ["add", "mul", "sub", "SL", "SRL", "SRA", "AND", "OR", "XOR", ">0", "=0", "mux", "branch", "merge"]
fu_dest_types = ["fu", "fu_delay", "branch1", "branch2"]

def normalize_names(name):
    """Return pretty-printed labels for checkboxes."""
    if name in ["fu_in1", "fu_in2", "fu_cin"]:
        return " " + name[:2].upper() + name[2:]
    if name in ["east", "west"]:
        return " " + name.capitalize() + " "
    return " " + name.capitalize()


# ------------------------------------------------------
# CGRA model and PE index mapping
# ------------------------------------------------------
rows, cols = 4, 4
cgra = CGRA(rows, cols)

def index_to_rc(idx):
    """Map linear index (column-major like original buttons) to (row, col)."""
    row = idx // rows
    col = idx % rows
    return row, col

def rc_to_index(row, col):
    """Map (row, col) to linear index in the original button layout."""
    return col + row * rows

# Current PE selection
pe_id = 0
cur_r, cur_c = index_to_rc(pe_id)
pe_config = cgra.pe_array[cur_r][cur_c]

# PE images (per-tile composited)
combined = [pe_base.copy() for _ in range(rows*cols)]

# ------------------------------------------------------
# Thin helpers to operate on ProcessingElement with GUI
# ------------------------------------------------------
ALU_OPS = {"add","mul","sub","SL","SRL","SRA","AND","OR","XOR"}
CMP_OPS = {">0","=0"}

def _get_input_obj(pe, border):
    """Return ProcessingElementInput object for a given border."""
    if border == "north": return pe.north_input
    if border == "east":  return pe.east_input
    if border == "south": return pe.south_input
    if border == "west":  return pe.west_input
    raise ValueError(f"Invalid border: {border}")

def _get_output_obj(pe, border):
    """Return ProcessingElementOutput object for a given border."""
    if border == "north": return pe.north_output
    if border == "east":  return pe.east_output
    if border == "south": return pe.south_output
    if border == "west":  return pe.west_output
    raise ValueError(f"Invalid border: {border}")

def _get_fu_input_obj(pe, fu_input):
    if fu_input == "fu_in1": return pe.fu_in1_mux
    if fu_input == "fu_in2": return pe.fu_in2_mux
    if fu_input == "fu_cin": return pe.fu_cin_mux
    raise ValueError(f"Invalid FU input: {fu_input}")

# --- Inputs: enable/disable and destinations ---
def get_pe_input(border):
    """Return True if the given input is enabled (EB or any FS destination)."""
    inp = _get_input_obj(pe_config, border)
    return bool(inp.elastic_buffer.get() or inp.fork_sender.get())

def set_pe_input(border):
    """Enable the given input (turn on its elastic buffer)."""
    inp = _get_input_obj(pe_config, border)
    inp.elastic_buffer.set()

def unset_pe_input(border):
    """Disable the given input: clear FS and reset EB if no destinations remain."""
    inp = _get_input_obj(pe_config, border)
    for d in list(inp.fork_sender.get()):
        inp.reset(d)
    inp.elastic_buffer.reset()

def get_input_destinations(border, dest):
    """Return True if 'dest' is currently selected in the input ForkSender."""
    inp = _get_input_obj(pe_config, border)
    return dest in inp.fork_sender.get()

def set_input_destinations(border, dest):
    """Add 'dest' to the input ForkSender and enable EB."""
    inp = _get_input_obj(pe_config, border)
    inp.set(dest)
    if dest in ["north", "east", "south", "west"]:
        _set_output_type(dest, border)
    elif dest == "fu_in1":
        pe_config.fu_in1_mux.set(border)
    elif dest == "fu_in2":
        pe_config.fu_in2_mux.set(border)
    elif dest == "fu_cin":
        pe_config.fu_cin_mux.set(border)

def unset_input_destinations(border, dest):
    """Remove 'dest' from the input ForkSender; if empty, reset EB."""
    inp = _get_input_obj(pe_config, border)
    inp.reset(dest)
    if dest in ["north", "east", "south", "west"]:
        out = _get_output_obj(pe_config, border)
        if dest == out.get():
            out.reset()
    elif dest == "fu_in1":
        fu_in = _get_fu_input_obj(pe_config, "fu_in1")
        if dest == fu_in.get():
            fu_in.reset()
    elif dest == "fu_in2":
        fu_in = _get_fu_input_obj(pe_config, "fu_in2")
        if dest == fu_in.get():
            fu_in.reset()
    elif dest == "fu_cin":
        fu_in = _get_fu_input_obj(pe_config, "fu_cin")
        if dest == fu_in.get():
            fu_in.reset()

# --- FU operation and parameters ---
def get_fu_operation():
    """Return a readable FU operation string (ALU op, cmp op, or 'mux')."""
    op_kind = pe_config.fu.fu_op.get()
    if op_kind == "alu":
        return pe_config.fu.alu_op.get()
    if op_kind == "cmp":
        return pe_config.fu.cmp_op.get()
    return "mux"

def set_fu_operation(op):
    """Set FU operation kind and specific op."""
    if op in ALU_OPS:
        pe_config.fu.fu_op.set("alu")
        pe_config.fu.alu_op.set(op)
    elif op in CMP_OPS:
        pe_config.fu.fu_op.set("cmp")
        pe_config.fu.cmp_op.set(op)
    elif op == "mux":
        pe_config.fu.fu_op.set("mux")
    else:
        # Fallback to ALU 'add'
        pe_config.fu.fu_op.set("alu")
        pe_config.fu.alu_op.set("add")

def get_fu_feedback():
    return pe_config.fu.feedback

def set_fu_feedback():
    pe_config.fu.set_feedback()

def unset_fu_feedback():
    pe_config.fu.reset_feedback()

def get_constant_value():
    return pe_config.fu.constant

def set_constant_value(val):
    pe_config.fu.set_constant(int(val))

def get_initial_value():
    return pe_config.fu.initial_value

def set_initial_value(val):
    pe_config.fu.set_initial_value(int(val))

def get_initial_valid():
    return pe_config.fu.initial_valid

def set_initial_valid():
    pe_config.fu.set_initial_valid(True)

def unset_initial_valid():
    pe_config.fu.set_initial_valid(False)

def get_delay_value():
    return pe_config.fu.delay_value

def set_delay_value(val):
    pe_config.fu.set_delay_value(int(val))

# --- FU inputs (const routing) ---
def set_constant_fu_in1():
    pe_config.fu_in1_mux.set("const")

def unset_constant_fu_in1():
    if pe_config.fu_in1_mux.get() == "const":
        pe_config.fu_in1_mux.reset()

def set_constant_fu_in2():
    pe_config.fu_in2_mux.set("const")

def unset_constant_fu_in2():
    if pe_config.fu_in2_mux.get() == "const":
        pe_config.fu_in2_mux.reset()

def get_fu_input_any(name):
    """Return True if any PE input routes to fu_in1 / fu_in2 / fu_cin."""
    dest = name  # "fu_in1" | "fu_in2" | "fu_cin"
    for b in ["north","east","south","west"]:
        inp = _get_input_obj(pe_config, b)
        if dest in inp.fork_sender.get():
            return True
    return False

# --- FU → Outputs wiring ---
def get_fu_destination(border):
    """Return True if FU output ForkSender targets the given border."""
    return border in pe_config.fu_out.get()

def set_fu_destination(border):
    pe_config.fu_out.set(border)

def unset_fu_destination(border):
    if border in pe_config.fu_out.get():
        pe_config.fu_out.reset(border)

def get_delay(border):
    """Return True if output valid_mux is 'fu_d' (delay)."""
    out = _get_output_obj(pe_config, border)
    return out.valid_mux.get() == "fu_d"

def get_branch1_output(border):
    out = _get_output_obj(pe_config, border)
    return out.valid_mux.get() == "fu_b1"

def get_branch2_output(border):
    out = _get_output_obj(pe_config, border)
    return out.valid_mux.get() == "fu_b2"

# --- Outputs: enable/disable ---
def _set_output_type(border, kind):
    """
    Set output type for a given border.
    kind in {"fu","fu_delay","branch1","branch2"}:
      - "fu"       -> select "fu"
      - "fu_delay" -> select "fu_d"
      - "branch1"  -> select "fu_b1"
      - "branch2"  -> select "fu_b2"
    """
    out = _get_output_obj(pe_config, border)
    if kind == "fu":
        out.set("fu")
    elif kind == "fu_delay":
        out.set("fu_d")
    elif kind == "branch1":
        out.set("fu_b1")
    elif kind == "branch2":
        out.set("fu_b2")
    else:
        out.set(kind)

def _unset_output_type(border):
    out = _get_output_obj(pe_config, border)
    out.reset()

# ============================================
#  CGRA window
# ============================================
cgra_window = tk.Tk()
cgra_window.title("CGRA configuration")

# Prepare image tiles
pe_tk_images = []
for i in range(rows*cols):
    pe_tk_images.append(ImageTk.PhotoImage(combined[i].resize((150, 150), Image.LANCZOS)))
pe_img_refs = []

def update_pe_id(index):
    """Switch current PE selection to index, refresh GUI."""
    global pe_id, pe_config, cur_r, cur_c
    pe_id = index
    cur_r, cur_c = index_to_rc(pe_id)
    pe_config = cgra.pe_array[cur_r][cur_c]
    update_gui_from_pe()

pe_buttons = []
for row in range(rows):
    for col in range(cols):
        index = rc_to_index(row, col)
        btn = tk.Button(
            cgra_window,
            image=pe_tk_images[index],
            command=lambda i=index: update_pe_id(i),
            background=cgra_window["background"],
            activebackground=cgra_window["background"],
            borderwidth=0
        )
        btn.grid(row=row, column=col, padx=5, pady=5)
        pe_img_refs.append(pe_tk_images[index])
        pe_buttons.append(btn)

def update_pe_images(index):
    """Refresh a single tile image."""
    updated_img = combined[index].resize((150, 150), Image.LANCZOS)
    tk_img = ImageTk.PhotoImage(updated_img)
    pe_tk_images[index] = tk_img
    pe_buttons[index].config(image=tk_img)
    pe_buttons[index].image = tk_img

def update_gui_from_pe():
    """Populate GUI widgets from the current ProcessingElement state."""
    # Inputs enable
    var_north_in.set(get_pe_input("north"))
    var_east_in.set(get_pe_input("east"))
    var_south_in.set(get_pe_input("south"))
    var_west_in.set(get_pe_input("west"))

    # Input destinations
    for dest in north_dest_order:
        north_dest_vars[dest].set(get_input_destinations("north", dest))
    for dest in east_dest_order:
        east_dest_vars[dest].set(get_input_destinations("east", dest))
    for dest in south_dest_order:
        south_dest_vars[dest].set(get_input_destinations("south", dest))
    for dest in west_dest_order:
        west_dest_vars[dest].set(get_input_destinations("west", dest))
    
    # Constant routing checkboxes (already present)
    const_fu_in1.set(pe_config.fu_in1_mux.get() == "const")
    const_fu_in2.set(pe_config.fu_in2_mux.get() == "const")

    # NEW: FU input elastic buffers (clock-gates) state
    fu1_cg.set(pe_config.fu_in1_elastic_buffer.get())
    fu2_cg.set(pe_config.fu_in2_elastic_buffer.get())


    # FU op and extras
    join_mode.set(pe_config.fu.join.get())
    fu_operation.set(pe_config.fu.alu_op.get())
    cmp_operation.set(pe_config.fu.cmp_op.get())
    fu_output.set(pe_config.fu.fu_op.get())
    feedback.set(get_fu_feedback())
    const_value.set(str(get_constant_value()))
    delay_value.set(get_delay_value())

    # Initial value/valid are always visible in superpolyvalent mode
    initial_value.set(str(get_initial_value()))
    initial_valid.set(get_initial_valid())

    # Constant routing checkboxes (sync with current PE mux selections)
    # True if FU input mux source is "const"; this prevents stale state when switching PEs.
    const_fu_in1.set(pe_config.fu_in1_mux.get() == "const")
    const_fu_in2.set(pe_config.fu_in2_mux.get() == "const")

    # FU -> outputs checkboxes (whether FU targets that border)
    var_north_out.set(get_fu_destination("north"))
    var_east_out.set(get_fu_destination("east"))
    var_south_out.set(get_fu_destination("south"))
    var_west_out.set(get_fu_destination("west"))

    # Output type comboboxes
    if get_delay("north"):
        fu_north_type.set("fu_delay")
    elif get_branch1_output("north"):
        fu_north_type.set("branch1")
    elif get_branch2_output("north"):
        fu_north_type.set("branch2")
    else:
        fu_north_type.set("fu")

    if get_delay("east"):
        fu_east_type.set("fu_delay")
    elif get_branch1_output("east"):
        fu_east_type.set("branch1")
    elif get_branch2_output("east"):
        fu_east_type.set("branch2")
    else:
        fu_east_type.set("fu")

    if get_delay("south"):
        fu_south_type.set("fu_delay")
    elif get_branch1_output("south"):
        fu_south_type.set("branch1")
    elif get_branch2_output("south"):
        fu_south_type.set("branch2")
    else:
        fu_south_type.set("fu")

    if get_delay("west"):
        fu_west_type.set("fu_delay")
    elif get_branch1_output("west"):
        fu_west_type.set("branch1")
    elif get_branch2_output("west"):
        fu_west_type.set("branch2")
    else:
        fu_west_type.set("fu")

    update_image()

# ============================================
#  PE window (controls)
# ============================================
pe_window = tk.Toplevel(cgra_window)
pe_window.title("PE Configuration")

def update_bitstream():
    """Compute and display current PE bitstream."""
    bs = pe_config.bitstream()
    bitstream_str = ", ".join(f"W{i}: {(w & 0xFFFFFFFF):08X}" for i, w in enumerate(bs))
    bitstream_label.config(text=f"Bitstream:\n\n   {bitstream_str}")

def update_north_dest_checkboxes():
    for _, checkbox in north_dest_checkboxes.items():
        checkbox.pack(side="left")

def update_east_dest_checkboxes():
    for _, checkbox in east_dest_checkboxes.items():
        checkbox.pack(side="left")

def update_south_dest_checkboxes():
    for _, checkbox in south_dest_checkboxes.items():
        checkbox.pack(side="left")

def update_west_dest_checkboxes():
    for _, checkbox in west_dest_checkboxes.items():
        checkbox.pack(side="left")

def update_join_mode(event):
    """Set FU join mode from the combobox."""
    try:
        pe_config.fu.join.set(join_mode.get())
    except Exception:
        pass
    update_bitstream()

def update_fu_operations():
    """
    Refresh FU-related comboboxes with sources from the model:
      - 'operations': ALU operations (fu.alu_op.sources)
      - 'cmp_box':    CMP operations (fu.cmp_op.sources)
      - 'fu_out_box': FU output mux (fu.fu_op.sources)
    It also ensures current selections match the active PE.
    """
    # ALU ops (e.g., add, mul, sub, SL, SRL, SRA, AND, OR, XOR)
    alu_ops = list(pe_config.fu.alu_op.sources)
    operations.config(values=alu_ops)
    if fu_operation.get() not in alu_ops:
        fu_operation.set(pe_config.fu.alu_op.get())

    # CMP ops (e.g., >0, =0)
    cmp_ops = list(pe_config.fu.cmp_op.sources)
    cmp_box.config(values=cmp_ops)
    if cmp_operation.get() not in cmp_ops:
        cmp_operation.set(pe_config.fu.cmp_op.get())

    # FU output ('alu', 'cmp', 'mux')
    fu_out_ops = list(pe_config.fu.fu_op.sources)
    fu_out_box.config(values=fu_out_ops)
    if fu_output.get() not in fu_out_ops:
        fu_output.set(pe_config.fu.fu_op.get())
    
    # NEW: Join mode
    join_ops = list(pe_config.fu.join.sources)
    join_box.config(values=join_ops)
    if join_mode.get() not in join_ops:
        join_mode.set(pe_config.fu.join.get())

def update_cmp_operation(event):
    """Set FU CMP operation from the combobox without changing FU output selection."""
    try:
        pe_config.fu.cmp_op.set(cmp_operation.get())
    except Exception:
        pass
    update_bitstream()

def update_fu_output(event):
    """Set which FU sub-block drives the output: 'alu' | 'cmp' | 'mux'."""
    try:
        pe_config.fu.fu_op.set(fu_output.get())
    except Exception:
        pass
    update_bitstream()

def update_fu_parameters():
    # Always show initial value and initial valid (superpolyvalent)
    const_label.config(text="Constant:")
    initial_value_label.pack(side="left", padx=(5, 5))
    initial_value_entry.pack(side="left")
    initial_valid_checkbox.pack(side="left", padx=(10))

def update_fu_destinations():
    # Full set of FU destination types
    fu_north.config(values=fu_dest_types)
    fu_east.config(values=fu_dest_types)
    fu_south.config(values=fu_dest_types)
    fu_west.config(values=fu_dest_types)

def update_image():
    """Recompose the PE tile image from current GUI state and apply model changes."""
    combined[pe_id] = pe_base.copy()

    # --- North input ---
    if var_north_in.get():
        set_pe_input("north")
        combined[pe_id] = Image.alpha_composite(combined[pe_id], img_north_in)
        north_dest_frame.pack(side="left")
        update_north_dest_checkboxes()
        for dest, var in north_dest_vars.items():
            if var.get() and dest in north_dest_images:
                set_input_destinations("north", dest)
                combined[pe_id] = Image.alpha_composite(combined[pe_id], north_dest_images[dest])
            else:
                unset_input_destinations("north", dest)
    else:
        if get_pe_input("north"):
            unset_pe_input("north")
        north_dest_frame.pack_forget()

    # --- East input ---
    if var_east_in.get():
        set_pe_input("east")
        combined[pe_id] = Image.alpha_composite(combined[pe_id], img_east_in)
        east_dest_frame.pack(side="left")
        update_east_dest_checkboxes()
        for dest, var in east_dest_vars.items():
            if var.get() and dest in east_dest_images:
                set_input_destinations("east", dest)
                combined[pe_id] = Image.alpha_composite(combined[pe_id], east_dest_images[dest])
            else:
                unset_input_destinations("east", dest)
    else:
        if get_pe_input("east"):
            unset_pe_input("east")
        east_dest_frame.pack_forget()

    # --- South input ---
    if var_south_in.get():
        set_pe_input("south")
        combined[pe_id] = Image.alpha_composite(combined[pe_id], img_south_in)
        south_dest_frame.pack(side="left")
        update_south_dest_checkboxes()
        for dest, var in south_dest_vars.items():
            if var.get() and dest in south_dest_images:
                set_input_destinations("south", dest)
                combined[pe_id] = Image.alpha_composite(combined[pe_id], south_dest_images[dest])
            else:
                unset_input_destinations("south", dest)
    else:
        if get_pe_input("south"):
            unset_pe_input("south")
        south_dest_frame.pack_forget()

    # --- West input ---
    if var_west_in.get():
        set_pe_input("west")
        combined[pe_id] = Image.alpha_composite(combined[pe_id], img_west_in)
        west_dest_frame.pack(side="left")
        update_west_dest_checkboxes()
        for dest, var in west_dest_vars.items():
            if var.get() and dest in west_dest_images:
                set_input_destinations("west", dest)
                combined[pe_id] = Image.alpha_composite(combined[pe_id], west_dest_images[dest])
            else:
                unset_input_destinations("west", dest)
    else:
        if get_pe_input("west"):
            unset_pe_input("west")
        west_dest_frame.pack_forget()

    # --- FU block overlay if any FU input used ---
    if get_fu_input_any("fu_in1") or get_fu_input_any("fu_in2") or get_fu_input_any("fu_cin"):
        combined[pe_id] = Image.alpha_composite(combined[pe_id], img_fu)

    # --- FU operation and parameters ---
    update_fu_operations()
    update_fu_parameters()

    try:
        pe_config.fu.join.set(join_mode.get() or pe_config.fu.join.get())
    except Exception:
        pass

    # Keep ALU op from combobox
    try:
        pe_config.fu.alu_op.set(fu_operation.get() or pe_config.fu.alu_op.get())
    except Exception:
        pass

    # Keep CMP op from combobox
    try:
        pe_config.fu.cmp_op.set(cmp_operation.get() or pe_config.fu.cmp_op.get())
    except Exception:
        pass

    # Keep FU output from combobox (which block drives the output)
    try:
        pe_config.fu.fu_op.set(fu_output.get() or pe_config.fu.fu_op.get())
    except Exception:
        pass

    if feedback.get():
        set_fu_feedback()
    else:
        unset_fu_feedback()

    # Constant and initial/valid
    try:
        set_constant_value(int(const_value.get(), 0))
    except ValueError:
        set_constant_value(0)

    try:
        set_initial_value(int(initial_value.get(), 0))
    except ValueError:
        set_initial_value(0)

    if initial_valid.get():
        set_initial_valid()
    else:
        unset_initial_valid()

    # Constant routing into FU inputs
    if const_fu_in1.get():
        set_constant_fu_in1()
    else:
        unset_constant_fu_in1()

    if const_fu_in2.get():
        set_constant_fu_in2()
    else:
        unset_constant_fu_in2()

    # Delay
    try:
        set_delay_value(int(delay_value.get(), 0))
    except ValueError:
        set_delay_value(0)

    # --- FU -> outputs ---
    update_fu_destinations()

    if var_north_out.get():
        set_fu_destination("north")
        north_fu_dest.pack(side="left")
        combined[pe_id] = Image.alpha_composite(combined[pe_id], img_fu_n)
        _set_output_type("north", fu_north_type.get() or "fu")
    else:
        unset_fu_destination("north")
        north_fu_dest.pack_forget()
        out = _get_output_obj(pe_config, "north")
        if out.get() in ["fu", "fu_d", "fu_b1", "fu_b2"]:
            _unset_output_type("north")

    if var_east_out.get():
        set_fu_destination("east")
        east_fu_dest.pack(side="left")
        combined[pe_id] = Image.alpha_composite(combined[pe_id], img_fu_e)
        _set_output_type("east", fu_east_type.get() or "fu")
    else:
        unset_fu_destination("east")
        east_fu_dest.pack_forget()
        out = _get_output_obj(pe_config, "east")
        if out.get() in ["fu", "fu_d", "fu_b1", "fu_b2"]:
            _unset_output_type("east")

    if var_south_out.get():
        set_fu_destination("south")
        south_fu_dest.pack(side="left")
        combined[pe_id] = Image.alpha_composite(combined[pe_id], img_fu_s)
        _set_output_type("south", fu_south_type.get() or "fu")
    else:
        unset_fu_destination("south")
        south_fu_dest.pack_forget()
        out = _get_output_obj(pe_config, "south")
        if out.get() in ["fu", "fu_d", "fu_b1", "fu_b2"]:
            _unset_output_type("south")

    if var_west_out.get():
        set_fu_destination("west")
        west_fu_dest.pack(side="left")
        combined[pe_id] = Image.alpha_composite(combined[pe_id], img_fu_w)
        _set_output_type("west", fu_west_type.get() or "fu")
    else:
        unset_fu_destination("west")
        west_fu_dest.pack_forget()
        out = _get_output_obj(pe_config, "west")
        if out.get() in ["fu", "fu_d", "fu_b1", "fu_b2"]:
            _unset_output_type("west")

    # Push recomposed image
    tk_img = ImageTk.PhotoImage(combined[pe_id])
    img_label.config(image=tk_img)
    img_label.image = tk_img

    update_bitstream()
    update_pe_images(pe_id)

def update_fu1_cg():
    if fu1_cg.get():
        pe_config.fu_in1_elastic_buffer.set()
    else:
        pe_config.fu_in1_elastic_buffer.reset()
    update_bitstream()

def update_fu2_cg():
    if fu2_cg.get():
        pe_config.fu_in2_elastic_buffer.set()
    else:
        pe_config.fu_in2_elastic_buffer.reset()
    update_bitstream()


def update_fu_operation(event):
    """Change ALU operation only; do not override FU output selection."""
    try:
        pe_config.fu.alu_op.set(fu_operation.get())
    except Exception:
        pass
    update_bitstream()

def update_feedback():
    if feedback.get():
        set_fu_feedback()
    else:
        unset_fu_feedback()
    update_bitstream()

def update_constant(*args):
    try:
        value = int(const_value.get(), 0)
    except ValueError:
        value = 0
    set_constant_value(value)
    update_bitstream()

def update_initial_value(*args):
    try:
        value = int(initial_value.get(), 0)
    except ValueError:
        value = 0
    set_initial_value(value)
    update_bitstream()

def update_initial_valid():
    if initial_valid.get():
        set_initial_valid()
    else:
        unset_initial_valid()
    update_bitstream()

def update_const_fu_in1():
    if const_fu_in1.get():
        set_constant_fu_in1()
    else:
        unset_constant_fu_in1()
    update_bitstream()

def update_const_fu_in2():
    if const_fu_in2.get():
        set_constant_fu_in2()
    else:
        unset_constant_fu_in2()
    update_bitstream()

def update_delay(*args):
    try:
        value = int(delay_value.get(), 0)
    except ValueError:
        value = 0
    set_delay_value(value)
    update_bitstream()

def update_fu2north(event):
    set_fu_destination("north")
    _set_output_type("north", fu_north_type.get())
    update_bitstream()

def update_fu2east(event):
    set_fu_destination("east")
    _set_output_type("east", fu_east_type.get())
    update_bitstream()

def update_fu2south(event):
    set_fu_destination("south")
    _set_output_type("south", fu_south_type.get())
    update_bitstream()

def update_fu2west(event):
    set_fu_destination("west")
    _set_output_type("west", fu_west_type.get())
    update_bitstream()

# ------------------------------------------
# Static labels and controls (PE window)
# ------------------------------------------

# Removed: PE type selector (all PEs are superpolyvalent)

tk.Label(pe_window, text="PE inputs | Input destinations:", font=("Courier", 10), anchor="w", justify="left").pack(fill="x", padx=10, pady=5)

# Input enable checkboxes
var_north_in = tk.BooleanVar()
north_row_frame = tk.Frame(pe_window)
north_row_frame.pack(anchor="w", padx=20)

var_east_in = tk.BooleanVar()
east_row_frame = tk.Frame(pe_window)
east_row_frame.pack(anchor="w", padx=20)

var_south_in = tk.BooleanVar()
south_row_frame = tk.Frame(pe_window)
south_row_frame.pack(anchor="w", padx=20)

var_west_in = tk.BooleanVar()
west_row_frame = tk.Frame(pe_window)
west_row_frame.pack(anchor="w", padx=20)

tk.Checkbutton(north_row_frame, text=" North", variable=var_north_in, command=update_image).pack(side="left")
tk.Checkbutton(east_row_frame, text=" East ", variable=var_east_in, command=update_image).pack(side="left")
tk.Checkbutton(south_row_frame, text=" South", variable=var_south_in, command=update_image).pack(side="left")
tk.Checkbutton(west_row_frame, text=" West ", variable=var_west_in, command=update_image).pack(side="left")

# Destination checkboxes per input
north_dest_frame = tk.Frame(north_row_frame)
separator = ttk.Separator(north_dest_frame, orient="vertical")
separator.pack(side="left", fill="y", padx=5)
north_dest_vars = {}
north_dest_checkboxes = {}
for dest in north_dest_order:
    var = tk.BooleanVar()
    chk = tk.Checkbutton(north_dest_frame, text=normalize_names(dest), variable=var, command=update_image)
    north_dest_vars[dest] = var
    north_dest_checkboxes[dest] = chk

east_dest_frame = tk.Frame(east_row_frame)
separator = ttk.Separator(east_dest_frame, orient="vertical")
separator.pack(side="left", fill="y", padx=5)
east_dest_vars = {}
east_dest_checkboxes = {}
for dest in east_dest_order:
    var = tk.BooleanVar()
    chk = tk.Checkbutton(east_dest_frame, text=normalize_names(dest), variable=var, command=update_image)
    east_dest_vars[dest] = var
    east_dest_checkboxes[dest] = chk

south_dest_frame = tk.Frame(south_row_frame)
separator = ttk.Separator(south_dest_frame, orient="vertical")
separator.pack(side="left", fill="y", padx=5)
south_dest_vars = {}
south_dest_checkboxes = {}
for dest in south_dest_order:
    var = tk.BooleanVar()
    chk = tk.Checkbutton(south_dest_frame, text=normalize_names(dest), variable=var, command=update_image)
    south_dest_vars[dest] = var
    south_dest_checkboxes[dest] = chk

west_dest_frame = tk.Frame(west_row_frame)
separator = ttk.Separator(west_dest_frame, orient="vertical")
separator.pack(side="left", fill="y", padx=5)
west_dest_vars = {}
west_dest_checkboxes = {}
for dest in west_dest_order:
    var = tk.BooleanVar()
    chk = tk.Checkbutton(west_dest_frame, text=normalize_names(dest), variable=var, command=update_image)
    west_dest_vars[dest] = var
    west_dest_checkboxes[dest] = chk

# Separator before FU parameters
separator = ttk.Separator(pe_window, orient='horizontal')
separator.pack(fill='x', padx=10, pady=10)

# FU section
tk.Label(pe_window, text="FU configuration:", font=("Courier", 10), anchor="w", justify="left").pack(fill="x", padx=10, pady=5)

fu_frame0 = tk.Frame(pe_window)
fu_frame0.pack(padx= 20, pady=5, fill="x")

# FU input EB (clock-gate) checkboxes
fu1_cg = tk.BooleanVar()
fu2_cg = tk.BooleanVar()
tk.Checkbutton(fu_frame0, text=" FU1 enable", variable=fu1_cg, command=update_fu1_cg).pack(side="left", padx=(5, 10))
tk.Checkbutton(fu_frame0, text=" FU2 enable", variable=fu2_cg, command=update_fu2_cg).pack(side="left", padx=(0, 20))
# Join mode combobox (values from pe_config.fu.join.sources)
join_mode = tk.StringVar()
join_label = tk.Label(fu_frame0, text="Join mode:")
join_label.pack(side="left", padx=(10, 5))
join_box = ttk.Combobox(fu_frame0, textvariable=join_mode, state='readonly')
join_box.pack(side="left")
join_box.bind("<<ComboboxSelected>>", update_join_mode)

fu_frame1 = tk.Frame(pe_window)
fu_frame1.pack(padx= 20, pady=5, fill="x")

fu_operation = tk.StringVar()
operations_label = tk.Label(fu_frame1, text="FU operation:")
operations_label.pack(side="left", padx=(5, 5))
operations = ttk.Combobox(fu_frame1, textvariable=fu_operation, values=fu_operations, state='readonly')
operations.current(0)
operations.pack(side="left", padx=(20))
operations.bind("<<ComboboxSelected>>", update_fu_operation)

feedback = tk.BooleanVar()
tk.Checkbutton(fu_frame1, text=" Feedback", variable=feedback, command=update_feedback).pack(side="left", padx=(10))

fu_frame_cmp = tk.Frame(pe_window)
fu_frame_cmp.pack(padx= 20, pady=5, fill="x")

# CMP operation (drives the FU comparator operation)
cmp_operation = tk.StringVar()
cmp_label = tk.Label(fu_frame_cmp, text="CMP operation:")
cmp_label.pack(side="left", padx=(5, 5))
cmp_box = ttk.Combobox(fu_frame_cmp, textvariable=cmp_operation, state='readonly')
cmp_box.pack(side="left")
cmp_box.bind("<<ComboboxSelected>>", update_cmp_operation)

fu_frame_out = tk.Frame(pe_window)
fu_frame_out.pack(padx= 20, pady=5, fill="x")

# FU output (select which sub-block drives the FU output)
fu_output = tk.StringVar()
fu_out_label = tk.Label(fu_frame_out, text="FU output:")
fu_out_label.pack(side="left", padx=(5, 5))
fu_out_box = ttk.Combobox(fu_frame_out, textvariable=fu_output, state='readonly')
fu_out_box.pack(side="left")
fu_out_box.bind("<<ComboboxSelected>>", update_fu_output)

const_value = tk.StringVar()
initial_value = tk.StringVar()
initial_valid = tk.BooleanVar()

fu_frame2 = tk.Frame(pe_window)
fu_frame2.pack(padx= 20, pady=5, fill="x")
const_label = tk.Label(fu_frame2, text="Constant:")
const_label.pack(side="left", padx=(5, 5))
const_entry = tk.Entry(fu_frame2, textvariable=const_value, width=10)
const_entry.insert(0, "0")
const_entry.pack(side="left")

initial_value_label = tk.Label(fu_frame2, text="Initial value:")
initial_value_label.pack(side="left", padx=(5, 5))
initial_value_entry = tk.Entry(fu_frame2, textvariable=initial_value, width=10)
initial_value_entry.insert(0, "0")
initial_value_entry.pack(side="left")

initial_valid_checkbox = tk.Checkbutton(fu_frame2, text=" Initial valid", variable=initial_valid, command=update_initial_valid)
initial_valid_checkbox.pack(side="left", padx=(10))

const_value.trace_add("write", update_constant)
initial_value.trace_add("write", update_initial_value)

# Constant usage
const_fu_in1 = tk.BooleanVar()
const_fu_in2 = tk.BooleanVar()

fu_frame3 = tk.Frame(pe_window)
fu_frame3.pack(padx=20 ,pady=5, fill="x")
tk.Label(fu_frame3, text="Constant destination:").pack(side="left", padx=(5, 5))
tk.Checkbutton(fu_frame3, text=" FU_in1", variable=const_fu_in1, command=update_const_fu_in1).pack(side="left", padx=(10))
tk.Checkbutton(fu_frame3, text=" FU_in2", variable=const_fu_in2, command=update_const_fu_in2).pack(side="left", padx=(10))

# Delay
fu_frame4 = tk.Frame(pe_window)
fu_frame4.pack(padx=20 ,pady=5, fill="x")
tk.Label(fu_frame4, text="Delay value:").pack(side="left", padx=(5, 5))
delay_value = tk.StringVar()
delay_entry = tk.Entry(fu_frame4, textvariable=delay_value, width=10)
delay_entry.insert(0, "0")
delay_entry.pack(side="left")
delay_value.trace_add("write", update_delay)

# Separator before FU destinations
separator = ttk.Separator(pe_window, orient='horizontal')
separator.pack(fill='x', padx=10, pady=10)

# FU destinations label
tk.Label(pe_window, text="FU destinations:", font=("Courier", 10), anchor="w", justify="left").pack(fill="x", padx=10, pady=5)

# FU destination checkboxes and combobox per side
var_north_out = tk.BooleanVar()
north_row_frame2 = tk.Frame(pe_window)
north_row_frame2.pack(anchor="w", padx=20)

var_east_out = tk.BooleanVar()
east_row_frame2 = tk.Frame(pe_window)
east_row_frame2.pack(anchor="w", padx=20)

var_south_out = tk.BooleanVar()
south_row_frame2 = tk.Frame(pe_window)
south_row_frame2.pack(anchor="w", padx=20)

var_west_out = tk.BooleanVar()
west_row_frame2 = tk.Frame(pe_window)
west_row_frame2.pack(anchor="w", padx=20)

tk.Checkbutton(north_row_frame2, text=" North", variable=var_north_out, command=update_image).pack(side="left")
tk.Checkbutton(east_row_frame2, text=" East ", variable=var_east_out, command=update_image).pack(side="left")
tk.Checkbutton(south_row_frame2, text=" South", variable=var_south_out, command=update_image).pack(side="left")
tk.Checkbutton(west_row_frame2, text=" West ", variable=var_west_out, command=update_image).pack(side="left")

# North combobox
north_fu_dest = tk.Frame(north_row_frame2)
separator = ttk.Separator(north_fu_dest, orient="vertical")
separator.pack(side="left", fill="y", padx=5)
fu_north_type = tk.StringVar()
fu_north = ttk.Combobox(north_fu_dest, textvariable=fu_north_type, values=fu_dest_types, state='readonly')
fu_north.current(0)
fu_north.pack(side="left", padx=(20))
fu_north.bind("<<ComboboxSelected>>", update_fu2north)

# East combobox
east_fu_dest = tk.Frame(east_row_frame2)
separator = ttk.Separator(east_fu_dest, orient="vertical")
separator.pack(side="left", fill="y", padx=5)
fu_east_type = tk.StringVar()
fu_east = ttk.Combobox(east_fu_dest, textvariable=fu_east_type, values=fu_dest_types, state='readonly')
fu_east.current(0)
fu_east.pack(side="left", padx=(20))
fu_east.bind("<<ComboboxSelected>>", update_fu2east)

# South combobox
south_fu_dest = tk.Frame(south_row_frame2)
separator = ttk.Separator(south_fu_dest, orient="vertical")
separator.pack(side="left", fill="y", padx=5)
fu_south_type = tk.StringVar()
fu_south = ttk.Combobox(south_fu_dest, textvariable=fu_south_type, values=fu_dest_types, state='readonly')
fu_south.current(0)
fu_south.pack(side="left", padx=(20))
fu_south.bind("<<ComboboxSelected>>", update_fu2south)

# West combobox
west_fu_dest = tk.Frame(west_row_frame2)
separator = ttk.Separator(west_fu_dest, orient="vertical")
separator.pack(side="left", fill="y", padx=5)
fu_west_type = tk.StringVar()
fu_west = ttk.Combobox(west_fu_dest, textvariable=fu_west_type, values=fu_dest_types, state='readonly')
fu_west.current(0)
fu_west.pack(side="left", padx=(20))
fu_west.bind("<<ComboboxSelected>>", update_fu2west)

# Separator before preview image
separator = ttk.Separator(pe_window, orient='horizontal')
separator.pack(fill='x', padx=10, pady=10)

# Preview image label
init_img = ImageTk.PhotoImage(pe_base)
img_label = tk.Label(pe_window, image=init_img)
img_label.image = init_img
img_label.pack(padx=10, pady=10)

separator = ttk.Separator(pe_window, orient='horizontal')
separator.pack(fill='x', padx=10, pady=10)

# Bitstream display
bitstream_label = tk.Label(pe_window, text="Bitstream: N/A", font=("Courier", 10), anchor="w", justify="left")
bitstream_label.pack(fill="x", padx=10, pady=5)
bitstream_str = ", ".join(f"W{i}: {(w & 0xFFFFFFFF):08X}" for i, w in enumerate(pe_config.bitstream()))
bitstream_label.config(text=f"Bitstream:\n\n   {bitstream_str}")

# ============================================
#  CLI and file I/O using CGRA helpers
# ============================================
def main():
    parser = argparse.ArgumentParser(description="CGRA bitstream GUI")
    parser.add_argument("--input", type=str, help="Path to the input bitstream (.bin only)")
    parser.add_argument("--output", type=str, help="Path to the output bitstream (.bin)")
    parser.add_argument("--cheader", type=str, help="Path to the output C header (.h)")
    parser.add_argument("--array-name", type=str, default="bypass_kernel", help="C array name for the header")
    args = parser.parse_args()

    # Import: only allowed from .bin
    if args.input:
        if not args.input.lower().endswith(".bin"):
            raise ValueError("Input must be a .bin file")
        print(f"Reading bitstream from: {args.input}")
        cgra.load_bin(args.input)
        # Refresh all tiles from the model
        for idx in range(rows*cols):
            update_pe_id(idx)

    # Start GUI
    cgra_window.mainloop()

    # Export: allow writing both BIN and C header in the same run
    if args.output:
        print(f"Writing bitstream to: {args.output}")
        cgra.write_bin(args.output)

    if args.cheader:
        print(f"Writing C header to: {args.cheader} (array: {args.array-name if hasattr(args,'array-name') else args.array_name})")
        cgra.write_c_header(args.array_name, args.cheader)

if __name__ == "__main__":
    main()
