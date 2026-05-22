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
        self.operation_list = ['add','mul','sub','SL','SRL','SRA','AND','OR','XOR','>0','=0','mux','branch','merge']

        self.join = Mux(['join_wo_c','join_w_c','merge'])
        self.alu_op = Mux(['add','mul','sub','SL','SRL','SRA','AND','OR','XOR'])
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
    def __init__(self):
        # Inputs
        self.north_input = ProcessingElementInput("north", ["west", "south", "east", "fu_cin", "fu_in2", "fu_in1"])
        self.east_input = ProcessingElementInput("east", ["west", "south", "north", "fu_cin", "fu_in2", "fu_in1"])
        self.south_input = ProcessingElementInput("south", ["west", "east", "north", "fu_cin", "fu_in2", "fu_in1"])
        self.west_input = ProcessingElementInput("west", ["south", "east", "north", "fu_cin", "fu_in2", "fu_in1"])

        # FU inputs
        self.fu_in1_elastic_buffer = ElasticBuffer()
        self.fu_in1_mux = Mux(["north", "east", "south", "west", "const", "fu"])

        self.fu_in2_elastic_buffer = ElasticBuffer()
        self.fu_in2_mux = Mux(["north", "east", "south", "west", "const", "fu"])

        self.fu_cin_mux = Mux(["north", "east", "south", "west"])

        # FU
        self.fu = FunctionalUnit()

        # FU output
        self.fu_out = ForkSender(["west", "south", "east", "north", "fu_in1", "fu_in2"])

        # Outputs
        self.north_output = ProcessingElementOutput("north", ["east", "south", "west"], ["fu", "fu_d", "fu_b1", "fu_b2"])
        self.east_output = ProcessingElementOutput("east", ["north", "south", "west"], ["fu", "fu_d", "fu_b1", "fu_b2"])
        self.south_output = ProcessingElementOutput("south", ["north", "east", "west"], ["fu", "fu_d", "fu_b1", "fu_b2"])
        self.west_output = ProcessingElementOutput("west", ["north", "east", "south"], ["fu", "fu_d", "fu_b1", "fu_b2"])

    def bitstream(self):
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

        word_1_2  = (fs_n << 0)  | (fs_e << 6)  | (fs_s << 12) | (fs_w << 18)
        word_1_2 |= (sel_n << 24) | (sel_e << 27) | (sel_s << 30) | (sel_w << 33)
        word_1_2 |= (sel_pc_1 << 36) | (sel_pc_2 << 39) | (sel_pc_c << 42) | (feedback << 44)
        word_1_2 |= (alu_sel << 45) | (cmp_sel << 49) | (out_sel << 50) | (fs_pc << 52)
        word_1_2 |= (jm_mode << 58) | (initial_valid << 60)

        word_1 = word_1_2 & 0xFFFFFFFF
        word_2 = (word_1_2 >> 32) & 0xFFFFFFFF
        word_3 = self.fu.initial_value & 0xFFFFFFFF
        word_4 = self.fu.constant & 0xFFFFFFFF

        # Clock gates
        ff_cgen_n   = int(self.north_input.elastic_buffer.configuration())
        ff_cgen_e   = int(self.east_input.elastic_buffer.configuration())
        ff_cgen_s   = int(self.south_input.elastic_buffer.configuration())
        ff_cgen_w   = int(self.west_input.elastic_buffer.configuration())
        ff_cgen_pc1 = int(self.fu_in1_elastic_buffer.configuration())
        ff_cgen_pc2 = int(self.fu_in2_elastic_buffer.configuration())

        word_5  = int(self.fu.delay_value) & 0xFFFFFFFF
        word_5 |= (ff_cgen_n << 26) | (ff_cgen_e << 27) | (ff_cgen_s << 28) | (ff_cgen_w << 29)
        word_5 |= (ff_cgen_pc1 << 30) | (ff_cgen_pc2 << 31)

        return [word_1, word_2, word_3, word_4, word_5]
    
    def from_bitstream(self, words):
        if len(words) != 5:
            raise ValueError("5 32-bits words were expected")
        w1, w2, w3, w4, w5 = (int(w) & 0xFFFFFFFF for w in words)
        word_1_2 = (w2 << 32) | w1

        def ext(v, lsb, width):
            return (v >> lsb) & ((1 << width) - 1)

        # Decode
        # Fork Senders inputs
        fs_n = ext(word_1_2,  0, 6)
        fs_e = ext(word_1_2,  6, 6)
        fs_s = ext(word_1_2, 12, 6)
        fs_w = ext(word_1_2, 18, 6)

        # PE outputs
        sel_n = ext(word_1_2, 24, 3)
        sel_e = ext(word_1_2, 27, 3)
        sel_s = ext(word_1_2, 30, 3)
        sel_w = ext(word_1_2, 33, 3)

        # FU inputs
        sel_pc_1 = ext(word_1_2, 36, 3)  # fu_in1_mux
        sel_pc_2 = ext(word_1_2, 39, 3)  # fu_in2_mux
        sel_pc_c = ext(word_1_2, 42, 2)  # fu_cin_mux

        feedback = ext(word_1_2, 44, 1)
        alu_sel  = ext(word_1_2, 45, 4)
        cmp_sel  = ext(word_1_2, 49, 1)
        out_sel  = ext(word_1_2, 50, 2)
        fs_pc    = ext(word_1_2, 52, 6)  # Fork Sender FU 
        jm_mode  = ext(word_1_2, 58, 2)  # join mode 
        initial_valid = ext(word_1_2, 60, 1)

        # Data
        initial_data_u32 = w3
        const_u32        = w4

        # Delay + FF flags
        delay_value_full = ext(w5, 0, 26)
        ff_cgen_n   = ext(w5, 26, 1)
        ff_cgen_e   = ext(w5, 27, 1)
        ff_cgen_s   = ext(w5, 28, 1)
        ff_cgen_w   = ext(w5, 29, 1)
        ff_cgen_pc1 = ext(w5, 30, 1)
        ff_cgen_pc2 = ext(w5, 31, 1)

        # Apply configuration
        def apply_fs(sender, mask):
            for idx, dest in enumerate(sender.destinations):
                bit = (mask >> idx) & 1
                if bit:
                    if dest not in sender.get():
                        sender.set(dest)
                else:
                    if dest in sender.get():
                        sender.reset(dest)

        apply_fs(self.north_input.fork_sender, fs_n)
        apply_fs(self.east_input.fork_sender,  fs_e)
        apply_fs(self.south_input.fork_sender, fs_s)
        apply_fs(self.west_input.fork_sender,  fs_w)

        if ff_cgen_n: self.north_input.elastic_buffer.set()
        else:         self.north_input.elastic_buffer.reset()

        if ff_cgen_e: self.east_input.elastic_buffer.set()
        else:         self.east_input.elastic_buffer.reset()

        if ff_cgen_s: self.south_input.elastic_buffer.set()
        else:         self.south_input.elastic_buffer.reset()

        if ff_cgen_w: self.west_input.elastic_buffer.set()
        else:         self.west_input.elastic_buffer.reset()

        def set_out_sel(pe_out, sel_idx):
            src = pe_out.valid_mux.sources[sel_idx]
            pe_out.set(src)

        set_out_sel(self.north_output, sel_n)
        set_out_sel(self.east_output,  sel_e)
        set_out_sel(self.south_output, sel_s)
        set_out_sel(self.west_output,  sel_w)

        self.fu_in1_mux.set(self.fu_in1_mux.sources[sel_pc_1])
        self.fu_in2_mux.set(self.fu_in2_mux.sources[sel_pc_2])
        self.fu_cin_mux.set(self.fu_cin_mux.sources[sel_pc_c])

        if ff_cgen_pc1: self.fu_in1_elastic_buffer.set()
        else:           self.fu_in1_elastic_buffer.reset()

        if ff_cgen_pc2: self.fu_in2_elastic_buffer.set()
        else:           self.fu_in2_elastic_buffer.reset()

        if feedback: self.fu.set_feedback()
        else:        self.fu.reset_feedback()

        self.fu.alu_op.set(self.fu.alu_op.sources[alu_sel])
        self.fu.cmp_op.set(self.fu.cmp_op.sources[cmp_sel])
        self.fu.fu_op.set(self.fu.fu_op.sources[out_sel])
        self.fu.join.set(self.fu.join.sources[jm_mode])

        self.fu.set_initial_valid(bool(initial_valid))

        apply_fs(self.fu_out, fs_pc)

        def to_s32(u32):
            return u32 - 0x100000000 if (u32 & 0x80000000) else u32

        self.fu.set_initial_value(to_s32(initial_data_u32))
        self.fu.set_constant(to_s32(const_u32))

        self.fu.set_delay_value(delay_value_full & 0xFFFF)


class CGRA:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols

        self.pe_array = [[ProcessingElement() for _ in range(cols)] for _ in range(rows)]
    
    def _iter_pe(self):
        """
        Iterate over Processing Elements in HW-like order
        """
        for c in range(self.cols):
            for r in range(self.rows):
                lin = r * self.cols + c
                yield r, c, lin, self.pe_array[r][c]

    def write_bin(self, filepath):
        """
        Generate a binary file containing the bitstream of all PEs.
        Each PE contributes 5 words (32-bit each), written in big-endian order.
        Iteration order: CGRA shift registers. North config border
        """
        with open(filepath, "wb") as f:
            for _, _, _, pe in self._iter_pe():
                words = pe.bitstream()
                if len(words) != 5:
                    raise ValueError("Each PE must return exactly 5 words in bitstream()")
                for w in words:
                    f.write(struct.pack(">I", int(w) & 0xFFFFFFFF))
    def write_c_header(self, array_name, filepath):
        """
        Generate a C header file with PE bitstreams.
        Output order (column-major for HW shift registers): 0, 4, 8, 12, 1, 5, 9, 13, ...
        Each PE needs 5 32-bit words.
        """
        npe = self.rows * self.cols
        lines = []
        lines.append("#include <stdint.h>\n\n")
        lines.append(f"#define NPE {npe}\n")
        lines.append(f"#define CONFIG_SIZE NPE * 5\n")
        lines.append(f"#define CONFIG_BYTES CONFIG_SIZE * 4\n\n")
        lines.append(f'uint32_t {array_name}[CONFIG_SIZE] __attribute__((section(".xheep_data_interleaved"))) = {{\n')

        for c in range(self.cols):
            for r in range(self.rows):
                pe_id = r * self.cols + c
                words = self.pe_array[r][c].bitstream()
                if len(words) != 5:
                    raise ValueError("Each PE must return exactly 5 words in bitstream()")

                hex_words = ", ".join(f"0x{(int(w) & 0xFFFFFFFF):08X}" for w in words)
                is_last = (c == self.cols - 1) and (r == self.rows - 1)
                comma = " " if is_last else ","
                lines.append(f"    {hex_words}{comma} // {pe_id}\n")

            if c != self.cols - 1:
                lines.append("\n")

        lines.append("};\n")

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)
    
    def load_bin(self, filepath):
        """
        Load a binary configuration file and configure all Processing Elements.
        Each PE consumes 5 consecutive 32-bit words (big-endian).
        The file must contain exactly NPE * 5 words.
        Iteration order: CGRA shift registers. North config border
        """
        npe = self.rows * self.cols
        total_words = npe * 5

        with open(filepath, "rb") as f:
            data = f.read()

        # Check
        if len(data) != total_words * 4:
            raise ValueError(
                f"Invalid file size: expected {total_words*4} bytes, got {len(data)} bytes"
            )

        # Read words as unsigned 32-bit (big-endian)
        words = list(struct.unpack(">" + "I" * total_words, data))

        # Iterate through PEs
        idx = 0
        for _, _, _, pe in self._iter_pe():
            pe_words = words[idx : idx + 5]
            pe.from_bitstream(pe_words)
            idx += 5
        