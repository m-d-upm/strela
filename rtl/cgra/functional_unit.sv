// Copyright 2026 CEIMM-UPM
// Solderpad Hardware License, Version 2.1, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Daniel Vazquez (daniel.vazquez@upm.es)

// Unified Functional Unit
//
// Operation encoding (alu_sel_i):
//   0 = ADD  (requires HAS_ADDSUB)
//   1 = SUB  (requires HAS_ADDSUB)
//   2 = MUL  (requires HAS_MUL)
//   3 = SHL  (requires HAS_SHIFT)
//   4 = SHR  (requires HAS_SHIFT)
//   5 = AND  (requires HAS_LOGICAL)
//   6 = OR   (requires HAS_LOGICAL)
//   7 = XOR  (requires HAS_LOGICAL)
//
// out_sel_i encoding:
//   0 = ALU output
//   1 = Comparator output (requires HAS_CMP)
//   2 = MUX output        (requires HAS_MUX)
//
// PE type equivalences:
//   L         : HAS_LOGICAL=1
//   A         : HAS_ADDSUB=1
//   M         : HAS_MUL=1
//   AML       : HAS_ADDSUB=1, HAS_MUL=1, HAS_LOGICAL=1
//   AMLCBMI   : HAS_ADDSUB=1, HAS_MUL=1, HAS_LOGICAL=1, HAS_CMP=1, HAS_MUX=1

module functional_unit #(
  parameter int DATA_WIDTH     = 32,
  parameter int N_DESTINATIONS = 6,
  // Operation enables (at least one must be set)
  parameter bit HAS_ADDSUB     = 1,   // Add / Subtract       (alu_sel 0, 2)
  parameter bit HAS_MUL        = 0,   // Multiply             (alu_sel 1)
  parameter bit HAS_SHIFT      = 0,   // Shift left / right   (alu_sel 3, 4)
  parameter bit HAS_LOGICAL    = 0,   // AND / OR / XOR       (alu_sel 5, 6, 7)
  // Feature enables
  parameter bit HAS_CMP        = 0,   // Comparator output    (out_sel 1)
  parameter bit HAS_MUX        = 0    // MUX / Branch via cin (out_sel 2)
) (
  // Clock and reset
  input logic clk_i,
  input logic rst_ni,
  input logic clr_i,

  // Configuration
  input logic [    DATA_WIDTH-1:0] initial_data_i,
  input logic                      initial_valid_i,
  input logic                      feedback_i,
  input logic [               2:0] alu_sel_i,
  input logic                      cmp_sel_i,        // HAS_CMP
  input logic [               1:0] out_sel_i,
  input logic [              15:0] delay_value_i,
  input logic [N_DESTINATIONS-1:0] fork_mask_i,

  // Data ports
  input  logic [DATA_WIDTH-1:0] din_1_i,
  input  logic [DATA_WIDTH-1:0] din_2_i,
  input  logic                  cin_i,    // HAS_MUX
  output logic [DATA_WIDTH-1:0] dout_o,

  // Valid/Ready ports
  input  logic in_v_i,
  output logic in_r_o,

  output logic out_v_o,
  output logic out_d_v_o,
  output logic out_b1_v_o,  // HAS_MUX
  output logic out_b2_v_o,  // HAS_MUX

  input logic [N_DESTINATIONS-1:0] out_r_i
);
  // synopsys sync_set_reset clr_i

  // ---------------------------------------------- //
  //                 INTERNAL SIGNALS               //
  // ---------------------------------------------- //

  logic [DATA_WIDTH-1:0] din_2;  // din_2 after feedback mux
  logic [DATA_WIDTH-1:0] addsub_dout;  // Add/sub result
  logic [DATA_WIDTH-1:0] mul_dout;  // Multiply result
  logic [DATA_WIDTH-1:0] shift_dout;  // Shift result
  logic [DATA_WIDTH-1:0] logical_dout;  // Logical result
  logic [DATA_WIDTH-1:0] alu_dout;  // Selected arithmetic result
  logic [DATA_WIDTH-1:0] cmp_dout;  // Comparator result
  logic [DATA_WIDTH-1:0] mux_dout;  // MUX result
  logic [DATA_WIDTH-1:0] pre_dout;  // Result before output register

  logic                  in_r;  // Raw ready from fork_sender
  logic                  initial_load;
  logic                  v_reg;
  logic                  b1_v;
  logic                  b1_v_reg;
  logic                  b2_v;
  logic                  b2_v_reg;
  logic [          15:0] delay_count;

  // ---------------------------------------------- //
  //               FEEDBACK MUX (din_2)             //
  // ---------------------------------------------- //

  assign din_2 = feedback_i ? (initial_load ? dout_o : initial_data_i) : din_2_i;

  // ---------------------------------------------- //
  //                  OPERATION UNITS               //
  // ---------------------------------------------- //

  // ---- Add / Subtract ----
  if (HAS_ADDSUB) begin : gen_addsub
    logic addsub_mode;
    // alu_sel 0 -> ADD (bit[0]=0), alu_sel 1 -> SUB (bit[0]=1)
    assign addsub_mode = alu_sel_i[0];

    adder_substracter #(
      .DATA_WIDTH(DATA_WIDTH)
    ) addsub_i (
      .a_i          (din_1_i),
      .b_i          (din_2),
      .addsub_mode_i(addsub_mode),
      .res_o        (addsub_dout)
    );
  end else begin : gen_no_addsub
    assign addsub_dout = '0;
  end

  // ---- Multiply ----
  if (HAS_MUL) begin : gen_mul
    multiplier_pe #(
      .DATA_WIDTH(DATA_WIDTH)
    ) mul_i (
      .a_i  (din_1_i),
      .b_i  (din_2),
      .res_o(mul_dout)
    );
  end else begin : gen_no_mul
    assign mul_dout = '0;
  end

  // ---- Shift left / right ----
  if (HAS_SHIFT) begin : gen_shift
    logic sr_mode;
    // alu_sel 3 -> SHL (sr_mode=0), alu_sel 4 -> SHR (sr_mode=1)
    assign sr_mode = (alu_sel_i == 3'd4);

    shifter #(
      .DATA_WIDTH(DATA_WIDTH)
    ) shift_i (
      .a_i      (din_1_i),
      .b_i      (din_2),
      .sr_mode_i(sr_mode),
      .res_o    (shift_dout)
    );
  end else begin : gen_no_shift
    assign shift_dout = '0;
  end

  // ---- Logical (AND / OR / XOR) ----
  if (HAS_LOGICAL) begin : gen_logical
    always_comb begin
      case (alu_sel_i)
        3'd5:    logical_dout = din_1_i & din_2;
        3'd6:    logical_dout = din_1_i | din_2;
        3'd7:    logical_dout = din_1_i ^ din_2;
        default: logical_dout = din_1_i & din_2;
      endcase
    end
  end else begin : gen_no_logical
    assign logical_dout = '0;
  end

  // ---- ALU output mux ----
  always_comb begin
    case (alu_sel_i)
      3'd0, 3'd1:       alu_dout = addsub_dout;
      3'd2:             alu_dout = mul_dout;
      3'd3, 3'd4:       alu_dout = shift_dout;
      3'd5, 3'd6, 3'd7: alu_dout = logical_dout;
      default:          alu_dout = addsub_dout;
    endcase
  end

  // ---------------------------------------------- //
  //                   COMPARATOR                   //
  // ---------------------------------------------- //

  if (HAS_CMP) begin : gen_cmp
    localparam logic [DATA_WIDTH-2:0] ZEROS = '0;
    logic cmp_eq, cmp_gr;
    assign cmp_eq = (alu_dout == '0);
    assign cmp_gr = ($signed(alu_dout) > 0);

    always_comb begin
      case (cmp_sel_i)
        1'b0:    cmp_dout = {ZEROS, cmp_eq};
        default: cmp_dout = {ZEROS, cmp_gr};
      endcase
    end
  end else begin : gen_no_cmp
    assign cmp_dout = '0;
  end

  // ---------------------------------------------- //
  //                      MUX                       //
  // ---------------------------------------------- //

  if (HAS_MUX) begin : gen_mux
    assign mux_dout = cin_i ? din_2_i : din_1_i;
    assign b1_v     = cin_i ? 1'b0 : in_v_i;
    assign b2_v     = cin_i ? in_v_i : 1'b0;
  end else begin : gen_no_mux
    assign mux_dout = '0;
    assign b1_v     = 1'b0;
    assign b2_v     = 1'b0;
  end

  // ---------------------------------------------- //
  //                 OUTPUT SELECTION               //
  // ---------------------------------------------- //

  always_comb begin
    case (out_sel_i)
      2'd0:    pre_dout = alu_dout;
      2'd1:    pre_dout = cmp_dout;
      default: pre_dout = mux_dout;
    endcase
  end

  // ---------------------------------------------- //
  //            REGISTERS & CONTROL                 //
  // ---------------------------------------------- //

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      dout_o       <= '0;
      initial_load <= 1'b0;
      delay_count  <= 16'd0;
      v_reg        <= 1'b0;
      b1_v_reg     <= 1'b0;
      b2_v_reg     <= 1'b0;
    end else begin
      if (clr_i) begin
        dout_o       <= '0;
        initial_load <= 1'b0;
        delay_count  <= 16'd0;
        v_reg        <= 1'b0;
        b1_v_reg     <= 1'b0;
        b2_v_reg     <= 1'b0;
      end else begin
        if (!initial_load) begin
          dout_o       <= initial_data_i;
          v_reg        <= initial_valid_i;
          initial_load <= 1'b1;
        end else begin
          if (in_r & in_v_i) begin
            dout_o <= pre_dout;
          end
          if (in_r) begin
            v_reg    <= in_v_i;
            b1_v_reg <= b1_v;
            b2_v_reg <= b2_v;
          end
        end

        if (initial_load && out_v_o && delay_value_i != 16'd0) begin
          if (delay_count + 1 == delay_value_i) begin
            delay_count  <= 16'd0;
            initial_load <= 1'b0;
          end else begin
            delay_count <= delay_count + 1;
          end
        end
      end
    end
  end

  assign out_v_o    = v_reg & in_r;
  assign out_d_v_o  = out_v_o & (delay_count + 1 == delay_value_i);
  assign out_b1_v_o = b1_v_reg & in_r;
  assign out_b2_v_o = b2_v_reg & in_r;
  assign in_r_o     = in_r && initial_load && !out_d_v_o;

  // ---------------------------------------------- //
  //                  FORK SENDER                   //
  // ---------------------------------------------- //

  fork_sender #(
    .NUM_READYS(N_DESTINATIONS)
  ) FS (
    .ready_in_o  (in_r),
    .readys_out_i(out_r_i),
    .fork_mask_i (fork_mask_i)
  );

endmodule
