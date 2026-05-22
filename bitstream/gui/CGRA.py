# Copyright 2025 CEI-UPM
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Solderpad Hardware License, Version 2.1, see LICENSE.md for details.
# Daniel Vazquez (daniel.vazquez@upm.es)

import struct
from math import ceil, log2


class ElasticBuffer:
    def __init__(self):
        self.config = False
    
    def set(self):
        self.config = True
    
    def reset(self):
        self.config = False
    
    def get(self):
        return self.config
    
    def configuration(self):
        return int(self.config)


class ForkSender:
    def __init__(self, destinations):
        self.n_destinations = len(destinations)
        self.destinations = destinations #.reverse()
        self.config_list = []
        self.config = 0
    
    def set(self, destination):
        if destination in self.destinations:
            self.config |= (1 << self.destinations.index(destination))
            if destination not in self.config_list:
                self.config_list.append(destination)
        else:
            raise ValueError(f"Invalid fork sender destination: {destination}")
    
    def reset(self, destination):
        if destination in self.destinations:
            self.config &= ~(1 << self.destinations.index(destination))
            if destination in self.config_list:
                self.config_list.remove(destination)
        else:
            raise ValueError(f"Invalid fork sender destination: {destination}")
    
    def get(self):
        return self.config_list

    def configuration(self):
        return self.config, self.n_destinations


class Mux:
    def __init__(self, sources):
        self.n_sources = len(sources)
        self.sources = sources
        self.config = 0
    
    def set(self, source):
        if source in self.sources:
            self.config = self.sources.index(source)
        else:
            raise ValueError(f"Invalid mux source: {source}")
    
    def reset(self):
        self.config = 0
    
    def get(self):
        return self.sources[self.config]
    
    def configuration(self):
        return self.config, ceil(log2(self.n_sources))


class FunctionalUnit:
    def __init__(self):
        self.join = Mux(['join_wo_c','join_w_c','merge'])
        self.alu_op = Mux(['add','sub','mul','SHF','SHFA','AND','OR','XOR'])
        self.feedback = False
        self.cmp_op = Mux(['=0','>0'])
        self.fu_op = Mux(['alu','cmp','mux'])
        self.initial_value = 0
        self.initial_valid = False
        self.constant = 0
        self.delay_value = 0

    # Join/Merge
    def set_join(self, mode):
        self.join.set(mode)
    
    def reset_join(self):
        self.join.reset()
    
    def get_join(self):
        return self.join.get()

    # ALU
    def set_alu_op(self, operation):
        self.alu_op.set(operation)
    
    def reset_alu_op(self):
        self.alu_op.reset()
    
    def get_alu_op(self):
        return self.alu_op.get()

    def set_feedback(self):
        self.feedback = True
    
    def reset_feedback(self):
        self.feedback = False
    
    def get_feedback(self):
        return self.feedback
    
    # CMP
    def set_cmp_op(self, operation):
        self.cmp_op.set(operation)
    
    def reset_cmp_op(self):
        self.cmp_op.reset()
    
    def get_cmp_op(self):
        return self.cmp_op.get()
    
    # FU output
    def set_fu_op(self, operation):
        self.fu_op.set(operation)
    
    def reset_fu_op(self):
        self.fu_op.reset()
    
    def get_fu_op(self):
        return self.fu_op.get()

    # Intial parameters
    def set_initial_value(self, value):
        if not (-2**31 <= value < 2**31):
            raise ValueError(f"initial_value {value} out of 32-bit signed range")
        self.initial_value = int(value)
    
    def get_initial_value(self):
        return self.initial_value

    def reset_initial_value(self):
        self.initial_value = 0

    def set_initial_valid(self, valid=True): 
        self.initial_valid = bool(valid)

    def get_initial_valid(self):
        return self.initial_valid

    def reset_initial_valid(self):
        self.initial_valid = False

    # Constant (signed 32-bit)
    def set_constant(self, value):
        if not (-2**31 <= value < 2**31):
            raise ValueError(f"constant {value} out of 32-bit signed range")
        self.constant = int(value)
    
    def get_constant(self):
        return self.constant

    def reset_constant(self):
        self.constant = 0

    # Delay (unsigned 16-bit)
    def set_delay_value(self, value):
        if not (0 <= value < 2**16):
            raise ValueError(f"delay_value {value} out of 16-bit unsigned range")
        self.delay_value = int(value)
    
    def get_delay_value(self):
        return self.delay_value

    def reset_delay_value(self):
        self.delay_value = 0

    def configuration(self):
        config = {}
        config["join"] = self.join.get()
        config["alu_op"] = self.alu_op.get()
        config["feedback"] = self.feedback
        config["cmp_op"] = self.cmp_op.get()
        config["fu_op"] = self.fu_op.get()
        config["initial_value"] = self.initial_value
        config["initial_valid"] = self.initial_valid
        config["constant"] = self.constant
        config["delay_value"] = self.delay_value
        return config


class ProcessingElementInput:
    def __init__(self, border, destinations):
        self.border = str(border)
        self.elastic_buffer = ElasticBuffer()
        self.fork_sender = ForkSender(destinations)

        if self.border in destinations:
            raise ValueError(f"Error: border '{self.border}' is also in destinations {destinations}")
        
    def set(self, destination):
        self.elastic_buffer.set()
        self.fork_sender.set(destination)
    
    def get(self):
        return self.fork_sender.get()
    
    def reset(self, destination):
        self.fork_sender.reset(destination)
        if not self.fork_sender.get():
            self.elastic_buffer.reset()
    
    def configuration(self):
        config = {}
        config["elastic_buffer"] = self.elastic_buffer.get()
        config["fork_sender"] = self.fork_sender.get()
        return config


class ProcessingElementOutput:
    def __init__(self, border, pe_sources, fu_sources):
        self.border = str(border)

        data_sources = list(pe_sources) + (["fu"] if fu_sources else [])
        valid_sources = pe_sources + fu_sources

        self.data_sources = data_sources

        self.data_mux = Mux(data_sources)
        self.valid_mux = Mux(valid_sources)

        if fu_sources and not "fu" in fu_sources:
            raise ValueError(f"Error: FU sources must contain at least the FU")

        if self.border in valid_sources:
            raise ValueError(f"Error: border '{border}' is also in sources {valid_sources}")
        
    def set(self, source):
        if source in self.data_sources:
            self.data_mux.set(source)
            self.valid_mux.set(source)
        else:
            self.data_mux.set("fu")
            self.valid_mux.set(source)

    def get(self):
        return self.valid_mux.get()
    
    def reset(self):
        self.data_mux.reset()
        self.valid_mux.reset()
    
    def configuration(self):
        config = {}
        config["data_mux"] = self.data_mux.get()
        config["valid_mux"] = self.valid_mux.get()
        return config


class ProcessingElement:
    def __init__(self, has_hvroutes=False):
        self.has_hvroutes = has_hvroutes

        # Inputs — destination order matches SV readys_out_i (index 0 = LSB = rightmost element)
        # FS_N: {din_1_r, din_2_r, cin_r, east_r, south_r, west_r} → [0]=west, [1]=south, [2]=east, [3]=cin, [4]=din2, [5]=din1
        self.north_input = ProcessingElementInput("north", ["west", "south", "east", "fu_cin", "fu_in2", "fu_in1"])
        # FS_E: {din_1_r, din_2_r, cin_r, north_r, south_r, west_r} → [0]=west, [1]=south, [2]=north, [3]=cin, [4]=din2, [5]=din1
        self.east_input  = ProcessingElementInput("east",  ["west", "south", "north", "fu_cin", "fu_in2", "fu_in1"])
        # FS_S: {din_1_r, din_2_r, cin_r, north_r, east_r, west_r}  → [0]=west, [1]=east, [2]=north, [3]=cin, [4]=din2, [5]=din1
        self.south_input = ProcessingElementInput("south", ["west", "east",  "north", "fu_cin", "fu_in2", "fu_in1"])
        # FS_W: {din_1_r, din_2_r, cin_r, north_r, east_r, south_r} → [0]=south, [1]=east, [2]=north, [3]=cin, [4]=din2, [5]=din1
        self.west_input  = ProcessingElementInput("west",  ["south", "east", "north", "fu_cin", "fu_in2", "fu_in1"])

        if has_hvroutes:
            # FS_V/FS_H: {cin_r, din_2_r, din_1_r} → [0]=din1, [1]=din2, [2]=cin
            self.ver_input = ForkSender(["fu_in1", "fu_in2", "fu_cin"])
            self.hor_input = ForkSender(["fu_in1", "fu_in2", "fu_cin"])

        # FU inputs — mux_i order: {hor, ver, dout, const, west, south, east, north} (NESWHV)
        #                        or {dout, const, west, south, east, north} (NESW)
        # Index 0 = north (LSB = rightmost), ascending toward MSB
        self.fu_in1_elastic_buffer = ElasticBuffer()
        if has_hvroutes:
            self.fu_in1_mux = Mux(["north", "east", "south", "west", "const", "fu", "ver", "hor"])
        else:
            self.fu_in1_mux = Mux(["north", "east", "south", "west", "const", "fu"])

        self.fu_in2_elastic_buffer = ElasticBuffer()
        if has_hvroutes:
            self.fu_in2_mux = Mux(["north", "east", "south", "west", "const", "fu", "ver", "hor"])
        else:
            self.fu_in2_mux = Mux(["north", "east", "south", "west", "const", "fu"])

        # MUX_C: {hor[0], ver[0], west[0], south[0], east[0], north[0]} (NESWHV)
        #      or {west[0], south[0], east[0], north[0]} (NESW)
        if has_hvroutes:
            self.fu_cin_mux = Mux(["north", "east", "south", "west", "ver", "hor"])
        else:
            self.fu_cin_mux = Mux(["north", "east", "south", "west"])

        # FU
        self.fu = FunctionalUnit()

        # FU output ForkSender — out_r_i order (NESWHV): {din_2_r, din_1_r, N_r, E_r, S_r, W_r, ver_r, hor_r}
        #   → index 0=hor, 1=ver, 2=west, 3=south, 4=east, 5=north, 6=fu_in1, 7=fu_in2
        # (NESW): {din_2_r, din_1_r, N_r, E_r, S_r, W_r}
        #   → index 0=west, 1=south, 2=east, 3=north, 4=fu_in1, 5=fu_in2
        if has_hvroutes:
            self.fu_out = ForkSender(["hor", "ver", "west", "south", "east", "north", "fu_in1", "fu_in2"])
        else:
            self.fu_out = ForkSender(["west", "south", "east", "north", "fu_in1", "fu_in2"])

        # Outputs — valid_mux source order matches SV MUX_*_v mux_i (index 0 = LSB = rightmost)
        self.north_output = ProcessingElementOutput("north", ["east", "south", "west"], ["fu", "fu_d", "fu_b1", "fu_b2"])
        self.east_output  = ProcessingElementOutput("east",  ["north", "south", "west"], ["fu", "fu_d", "fu_b1", "fu_b2"])
        self.south_output = ProcessingElementOutput("south", ["north", "east",  "west"], ["fu", "fu_d", "fu_b1", "fu_b2"])
        self.west_output  = ProcessingElementOutput("west",  ["north", "east",  "south"], ["fu", "fu_d", "fu_b1", "fu_b2"])

        if has_hvroutes:
            # MUX_V_v/MUX_H_v: {dout_b2_v, dout_b1_v, dout_d_v, dout_v} → [0]=fu, [1]=fu_d, [2]=fu_b1, [3]=fu_b2
            self.ver_output = Mux(["fu", "fu_d", "fu_b1", "fu_b2"])
            self.hor_output = Mux(["fu", "fu_d", "fu_b1", "fu_b2"])

    def bitstream(self):
        # PE inputs clock gates
        ff_cgen_n = int(self.north_input.elastic_buffer.configuration())
        ff_cgen_e = int(self.east_input.elastic_buffer.configuration())
        ff_cgen_s = int(self.south_input.elastic_buffer.configuration())
        ff_cgen_w = int(self.west_input.elastic_buffer.configuration())

        # Fork Sender masks from PE inputs (6 bits each)
        fs_n = int(self.north_input.fork_sender.configuration()[0])
        fs_e = int(self.east_input.fork_sender.configuration()[0])
        fs_s = int(self.south_input.fork_sender.configuration()[0])
        fs_w = int(self.west_input.fork_sender.configuration()[0])

        # Output data mux selections (north/east/south/west)
        sel_n = int(self.north_output.valid_mux.configuration()[0])
        sel_e = int(self.east_output.valid_mux.configuration()[0])
        sel_s = int(self.south_output.valid_mux.configuration()[0])
        sel_w = int(self.west_output.valid_mux.configuration()[0])

        if self.has_hvroutes:
            fs_v = int(self.ver_input.configuration()[0])
            fs_h = int(self.hor_input.configuration()[0])
            sel_v = int(self.ver_output.configuration()[0])
            sel_h = int(self.hor_output.configuration()[0])
        else:
            fs_v = fs_h = 0
            sel_v = sel_h = 0

        # FU inputs clock gates
        ff_cgen_pc1 = int(self.fu_in1_elastic_buffer.configuration())
        ff_cgen_pc2 = int(self.fu_in2_elastic_buffer.configuration())

        # FU input mux selections (pc_1 / pc_2 / pc_cin)
        sel_pc_1 = int(self.fu_in1_mux.configuration()[0])
        sel_pc_2 = int(self.fu_in2_mux.configuration()[0])
        sel_pc_c = int(self.fu_cin_mux.configuration()[0])

        # FU control selections
        feedback = int(self.fu.feedback)
        alu_sel  = int(self.fu.alu_op.configuration()[0])
        cmp_sel  = int(self.fu.cmp_op.configuration()[0])
        out_sel  = int(self.fu.fu_op.configuration()[0])
        fs_pc    = int(self.fu_out.configuration()[0])
        jm_mode  = int(self.fu.join.configuration()[0])
        initial_valid = int(self.fu.initial_valid)

        conf_word  = (ff_cgen_n << 0) | (ff_cgen_e << 1) | (ff_cgen_s << 2) | (ff_cgen_w << 3)
        conf_word |= (fs_n << 4)  | (fs_e << 10)  | (fs_s << 16) | (fs_w << 22) | (fs_v << 28) | (fs_h << 31)
        conf_word |= (sel_n << 34) | (sel_e << 37) | (sel_s << 40) | (sel_w << 43) | (sel_v << 46) | (sel_h << 48)
        conf_word |= (ff_cgen_pc1 << 50) | (ff_cgen_pc2 << 51)
        conf_word |= (sel_pc_1 << 52) | (sel_pc_2 << 55) | (sel_pc_c << 58) | (jm_mode << 61) | (feedback << 63)
        conf_word |= (alu_sel << 64) | (cmp_sel << 67) | (out_sel << 68) | (fs_pc << 70) | (initial_valid << 78)
        conf_word |= ((int(self.fu.delay_value) & 0xFFFF) << 80)
        conf_word |= ((int(self.fu.initial_value) & 0xFFFFFFFF) << 96)
        conf_word |= ((int(self.fu.constant) & 0xFFFFFFFF) << 128)

        word_1 = (conf_word >>   0) & 0xFFFFFFFF
        word_2 = (conf_word >>  32) & 0xFFFFFFFF
        word_3 = (conf_word >>  64) & 0xFFFFFFFF
        word_4 = (conf_word >>  96) & 0xFFFFFFFF
        word_5 = (conf_word >> 128) & 0xFFFFFFFF

        return [word_1, word_2, word_3, word_4, word_5]
    
    def from_bitstream(self, words):
        """
        Decoder for 5x32b words produced by bitstream()
        """
        if len(words) != 5:
            raise ValueError("5 32-bits words were expected")

        w1, w2, w3, w4, w5 = (int(w) & 0xFFFFFFFF for w in words)
        conf_word = (
            (w1 << 0)
            | (w2 << 32)
            | (w3 << 64)
            | (w4 << 96)
            | (w5 << 128)
        )

        def ext(v, lsb, width):
            return (v >> lsb) & ((1 << width) - 1)

        # -----------------------
        # Extract fields (v2)
        # -----------------------
        ff_cgen_n = ext(conf_word, 0, 1)
        ff_cgen_e = ext(conf_word, 1, 1)
        ff_cgen_s = ext(conf_word, 2, 1)
        ff_cgen_w = ext(conf_word, 3, 1)

        fs_n = ext(conf_word, 4, 6)
        fs_e = ext(conf_word, 10, 6)
        fs_s = ext(conf_word, 16, 6)
        fs_w = ext(conf_word, 22, 6)
        fs_v = ext(conf_word, 28, 3)
        fs_h = ext(conf_word, 31, 3)

        sel_n = ext(conf_word, 34, 3)
        sel_e = ext(conf_word, 37, 3)
        sel_s = ext(conf_word, 40, 3)
        sel_w = ext(conf_word, 43, 3)
        sel_v = ext(conf_word, 46, 2)
        sel_h = ext(conf_word, 48, 2)

        ff_cgen_pc1 = ext(conf_word, 50, 1)
        ff_cgen_pc2 = ext(conf_word, 51, 1)

        sel_pc_1 = ext(conf_word, 52, 3)
        sel_pc_2 = ext(conf_word, 55, 3)
        sel_pc_c = ext(conf_word, 58, 3)

        jm_mode   = ext(conf_word, 61, 2)
        feedback  = ext(conf_word, 63, 1)
        alu_sel = ext(conf_word, 64, 3)
        cmp_sel = ext(conf_word, 67, 1) 
        out_sel = ext(conf_word, 68, 2)
        fs_pc   = ext(conf_word, 70, 8)
        initial_valid = ext(conf_word, 78, 1)

        delay_value = ext(conf_word, 80, 16)
        initial_data_u32 = ext(conf_word, 96, 32)
        const_u32 = ext(conf_word, 128, 32)

        # -----------------------
        # Apply configuration
        # -----------------------
        def apply_fs(sender, mask):
            # Sync sender's bitmask to exactly 'mask'
            for idx, dest in enumerate(sender.destinations):
                bit = (mask >> idx) & 1
                if bit:
                    if dest not in sender.get():
                        sender.set(dest)
                else:
                    if dest in sender.get():
                        sender.reset(dest)

        # Input FS
        apply_fs(self.north_input.fork_sender, fs_n)
        apply_fs(self.east_input.fork_sender,  fs_e)
        apply_fs(self.south_input.fork_sender, fs_s)
        apply_fs(self.west_input.fork_sender,  fs_w)
        if self.has_hvroutes:
            apply_fs(self.ver_input, fs_v)
            apply_fs(self.hor_input, fs_h)

        # Input EBs
        self.north_input.elastic_buffer.set() if ff_cgen_n else self.north_input.elastic_buffer.reset()
        self.east_input.elastic_buffer.set()  if ff_cgen_e else self.east_input.elastic_buffer.reset()
        self.south_input.elastic_buffer.set() if ff_cgen_s else self.south_input.elastic_buffer.reset()
        self.west_input.elastic_buffer.set()  if ff_cgen_w else self.west_input.elastic_buffer.reset()

        # Output selections
        def set_out_sel(pe_out, sel_idx):
            src = pe_out.valid_mux.sources[sel_idx]
            pe_out.set(src)

        set_out_sel(self.north_output, sel_n)
        set_out_sel(self.east_output,  sel_e)
        set_out_sel(self.south_output, sel_s)
        set_out_sel(self.west_output,  sel_w)

        # Ver/Hor outputs are plain Mux (NESWHV only)
        if self.has_hvroutes:
            self.ver_output.set(self.ver_output.sources[sel_v])
            self.hor_output.set(self.hor_output.sources[sel_h])

        # FU inputs
        self.fu_in1_mux.set(self.fu_in1_mux.sources[sel_pc_1])
        self.fu_in2_mux.set(self.fu_in2_mux.sources[sel_pc_2])
        self.fu_cin_mux.set(self.fu_cin_mux.sources[sel_pc_c])

        # FU input EBs
        self.fu_in1_elastic_buffer.set() if ff_cgen_pc1 else self.fu_in1_elastic_buffer.reset()
        self.fu_in2_elastic_buffer.set() if ff_cgen_pc2 else self.fu_in2_elastic_buffer.reset()

        # FU control
        if feedback: self.fu.set_feedback()
        else:        self.fu.reset_feedback()

        # ALU/CMP/FU output/join
        self.fu.alu_op.set(self.fu.alu_op.sources[alu_sel % len(self.fu.alu_op.sources)])
        self.fu.cmp_op.set(self.fu.cmp_op.sources[cmp_sel % len(self.fu.cmp_op.sources)])
        self.fu.fu_op.set(self.fu.fu_op.sources[out_sel % len(self.fu.fu_op.sources)])
        self.fu.join.set(self.fu.join.sources[jm_mode % len(self.fu.join.sources)])

        # Initial valid
        self.fu.set_initial_valid(bool(initial_valid))

        # FU output FS
        apply_fs(self.fu_out, fs_pc)

        # Helpers to convert to signed 32-bit
        def to_s32(u32):
            return u32 - 0x100000000 if (u32 & 0x80000000) else u32

        self.fu.set_initial_value(to_s32(initial_data_u32))
        self.fu.set_constant(to_s32(const_u32))
        self.fu.set_delay_value(delay_value & 0xFFFF)

class Router:
    def __init__(self, sources, destinations):
        self.input = Mux(sources)
        self.elastic_buffer = ElasticBuffer()
        self.output = ForkSender(destinations)

    def bitstream(self):
        mux = int(self.input.configuration()[0])
        cg_en = self.elastic_buffer.configuration()
        fs = int(self.output.configuration()[0])
        conf_word = (mux << 0) | (cg_en << self.input.configuration()[1]) | (fs << self.input.configuration()[1] + 1)
        return conf_word & 0XFFFFFFFF, self.input.configuration()[1] + 1 + self.output.configuration()[1]

class RouterNode:
    def __init__(self):
        self.ver_router = Router(["ISE", "A", "B", "C", "D"], ["A", "B", "C", "D", "OSE"])
        self.hor_router = Router(["West", "A", "B", "C", "D", "East"], ["West","A", "B", "C", "D", "East"])

    def bitstream(self):
        conf_word = (self.ver_router.bitstream()[0] << 0) | (self.hor_router.bitstream()[0] << self.ver_router.bitstream()[1])
        return conf_word & 0XFFFFFFFF

class CGRA:
    def __init__(self, rows, cols, has_hvroutes=False):
        self.rows = rows
        self.cols = cols
        self.has_hvroutes = has_hvroutes

        self.pe_array = [[ProcessingElement(has_hvroutes) for _ in range(cols)] for _ in range(rows)]
        self.router_array = [RouterNode() for _ in range(cols)]
    
    def _iter_pe_linear(self):
        """
        Iterate over Processing Elements in column-major order.
        Linear index = col * rows + row.
        """
        for c in range(self.cols):
            for r in range(self.rows):
                lin = c * self.rows + r
                yield r, c, lin, self.pe_array[r][c]

    def write_bin(self, filepath):
        """
        Generate a binary file containing the bitstream of all PEs and, if
        has_hvroutes, one 32-bit word per router node appended at the end.
        - Each PE contributes 5 words (32-bit each), little-endian.
        - Each RouterNode contributes 1 word (32-bit), little-endian (hvroutes only).
        Iteration order for PEs: column-major (lin = col * rows + row).
        """
        import struct

        with open(filepath, "wb") as f:
            for c in range(self.cols):
                # Write all PEs in this column (top to bottom)
                for r in range(self.rows-1,-1,-1):
                    words = self.pe_array[r][c].bitstream()
                    if len(words) != 5:
                        raise ValueError("Each PE must return exactly 5 words in bitstream()")
                    for w in words:
                        f.write(struct.pack(">I", int(w) & 0xFFFFFFFF))
                # Append router node for this column when HV routes are enabled
                if self.has_hvroutes:
                    rn_word = int(self.router_array[c].bitstream()) & 0xFFFFFFFF
                    f.write(struct.pack(">I", rn_word))

    def write_c_header(self, array_name, filepath):
        """
        Generate a C header file with configuration constants and the bitstream
        laid out by column, bottom-to-top per column. When has_hvroutes is True,
        the router node word is interleaved after each column's PEs.

        Order for a 4x4 with hvroutes:
            12, 8, 4, 0, router0,  13, 9, 5, 1, router1, ...
        Order for a 4x4 without hvroutes:
            12, 8, 4, 0,  13, 9, 5, 1, ...

        - Each PE contributes 5 words (32-bit).
        - Each RouterNode contributes 1 word (32-bit) — hvroutes only.
        - The array length (CONFIG_SIZE) is NPE * 5 (+ NROUTERS if hvroutes).
        """

        lines = []
        lines.append("#include <stdint.h>\n")
        lines.append("#include \"strela.h\"\n\n")

        lines.append(f'uint32_t {array_name}[CONFIG_SIZE] __attribute__((section(".xheep_data_interleaved"))) = {{\n')

        # Emit column by column, bottom-to-top in each column.
        # When hvroutes, append the router node word after each column's PEs.
        for c in range(self.cols):
            # Emit PEs in this column from bottom (rows-1) to top (0)
            for r in range(self.rows - 1, -1, -1):
                pe_id = r * self.cols + c
                words = self.pe_array[r][c].bitstream()
                if len(words) != 5:
                    raise ValueError("Each PE must return exactly 5 words in bitstream()")
                hex_words = ", ".join(f"0x{(int(w) & 0xFFFFFFFF):08X}" for w in words)
                is_last_entry = (not self.has_hvroutes) and (c == self.cols - 1) and (r == 0)
                comma = "" if is_last_entry else ","
                lines.append(f"    {hex_words}{comma} // {pe_id}\n")

            if self.has_hvroutes:
                # Emit router node word for this column (single 32-bit word)
                rn_word = int(self.router_array[c].bitstream()) & 0xFFFFFFFF
                is_last_column = (c == self.cols - 1)
                comma = "" if is_last_column else ","
                lines.append(f"    0x{rn_word:08X}{comma} // routernode{c}\n")

            if c != self.cols - 1:
                lines.append("\n")  # blank line between column groups

        lines.append("};\n")

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def load_bin(self, filepath):
        """
        Load a binary configuration file and configure the CGRA.

        Supported formats:
        - PE-only (no hvroutes): NPE * 5 words
        - With router nodes (hvroutes): NPE * 5 + NROUTERS words
            * NPE      = rows * cols
            * NROUTERS = cols
        - Endianness: little-endian (matches write_bin)

        PE iteration order is column-major (lin = col * rows + row), same as write_bin.
        Router nodes are appended at the end (one 32-bit word per column), hvroutes only.

        Router node word layout (per column):
        word[8:0]   = vertical router (9-bit): mux[2:0] | cg_en[3] | fs_mask[8:4]
        word[17:9]  = horizontal router (9-bit): mux[2:0] | cg_en[3] | fs_mask[8:4]
        fs_mask bit i maps to router.output.destinations[i] order.
        """
        import struct

        npe = self.rows * self.cols
        nrouters = self.cols if self.has_hvroutes else 0
        pe_words_count = npe * 5
        min_words = pe_words_count
        max_words = pe_words_count + nrouters

        # Read entire file
        with open(filepath, "rb") as f:
            data = f.read()
        if len(data) % 4 != 0:
            raise ValueError(f"Invalid file size (not multiple of 4 bytes): {len(data)}")

        nwords = len(data) // 4
        if nwords not in (min_words, max_words):
            raise ValueError(
                f"Unexpected word count: got {nwords}, expected {min_words}"
                + (f" or {max_words} (with router nodes)" if self.has_hvroutes else "")
            )

        # Unpack unsigned 32-bit (little-endian)
        words = list(struct.unpack(">" + "I" * nwords, data))

        def apply_router(router, bits9: int):
            """Decode 9-bit field into router.input mux, elastic_buffer and output ForkSender."""
            bits9 = int(bits9) & 0x1FF
            mux_idx =  bits9        & 0b111     # [2:0]
            cg_en   = (bits9 >> 3)  & 0b1       # [3]
            fs_mask = (bits9 >> 4)  & 0b1_1111  # [8:4]

            # Input mux (index into router.input.sources)
            try:
                srcs = router.input.sources
                sel_index = mux_idx % len(srcs)
                router.input.set(srcs[sel_index])
            except Exception:
                pass

            # Elastic buffer (clock gate)
            if cg_en:
                router.elastic_buffer.set()
            else:
                router.elastic_buffer.reset()

            # ForkSender outputs: equalize exactly to fs_mask
            # First clear any active destinations
            for d in list(router.output.get()):
                router.output.reset(d)
            # Then apply mask in the order of destinations
            for i, dest in enumerate(router.output.destinations):
                if (fs_mask >> i) & 1:
                    router.output.set(dest)

        # Configure PEs and router nodes (column-major, router interleaved per column)
        idx = 0
        for c in range(self.cols):
            for r in range(self.rows-1,-1,-1):
                pe_words = words[idx: idx + 5]
                if len(pe_words) != 5:
                    raise ValueError("Corrupted file: incomplete PE record")
                self.pe_array[r][c].from_bitstream(pe_words)
                idx += 5

            if self.has_hvroutes and nwords == max_words:
                if not hasattr(self, "router_array") or len(self.router_array) != self.cols:
                    raise AttributeError(
                        "This bitstream contains router nodes but CGRA.router_array is missing "
                        "or has a wrong length."
                    )
                w = int(words[idx]) & 0xFFFFFFFF
                ver_bits = (w >> 0) & 0x1FF
                hor_bits = (w >> 9) & 0x1FF
                apply_router(self.router_array[c].ver_router, ver_bits)
                apply_router(self.router_array[c].hor_router, hor_bits)
                idx += 1
