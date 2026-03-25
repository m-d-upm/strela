// Copyright 2026 CEIMM-UPM
// Solderpad Hardware License, Version 2.1, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Daniel Vazquez (daniel.vazquez@upm.es)

// Unified Processing Element
//
// PE routing [45:0]:
//   [3:0]    eb_{n,e,s,w}_en
//   [9:4]    mask_fs_n  {din_1_r, din_2_r, cin_r, E_r, S_r, W_r}
//   [15:10]  mask_fs_e  {din_1_r, din_2_r, cin_r, N_r, S_r, W_r}
//   [21:16]  mask_fs_s  {din_1_r, din_2_r, cin_r, N_r, E_r, W_r}
//   [27:22]  mask_fs_w  {din_1_r, din_2_r, cin_r, N_r, E_r, S_r}
//   [33:28]  (reserved)
//   [36:34]  mux_sel_n
//   [39:37]  mux_sel_e
//   [42:40]  mux_sel_s
//   [45:43]  mux_sel_w
//   [49:46]  (reserved)
//
// Data path [159:50]
//   [50]     eb_fu1_en
//   [51]     eb_fu2_en
//   [54:52]  mux_sel_1   0=N 1=E 2=S 3=W 4=constant 5=dout(fb)
//   [57:55]  mux_sel_2   same encoding
//   [59:58]  mux_sel_c   0=N 1=E 2=S 3=W  (HAS_MUX only)
//   [60]     (reserved)
//   [62:61]  jm_mode
//   [63]     feedback
//   [66:64]  alu_sel     (see FU.sv encoding)
//   [67]     cmp_sel     (HAS_CMP only)
//   [69:68]  out_sel     0=ALU 1=CMP 2=MUX
//   [75:70]  mask_fs_fu  {din_2_r, din_1_r, N_r, E_r, S_r, W_r}
//   [77:76]  (reserved)
//   [78]     initial_valid
//   [79]     (reserved)
//   [95:80]  delay_value
//   [127:96] initial_data
//   [159:128] constant
//
// * When HAS_MUX=0, cin_r is tied to 1 and its mask bit must be set to 0.
//
// Output valid mux encoding (mux_sel_{n,e,s,w}), 7 options (3-bit sel):
//   0 = neighbor buffer 0    3 = dout_v    5 = dout_b1_v (HAS_MUX)
//   1 = neighbor buffer 1    4 = dout_d_v  6 = dout_b2_v (HAS_MUX)
//   2 = neighbor buffer 2
//
// Former PE type equivalences:
//   A       : HAS_ADDSUB=1
//   M       : HAS_MUL=1
//   L       : HAS_SHIFT=1, HAS_LOGICAL=1
//   AML     : HAS_ADDSUB=1, HAS_MUL=1, HAS_SHIFT=1, HAS_LOGICAL=1
//   AMLCBMI : HAS_ADDSUB=1, HAS_MUL=1, HAS_SHIFT=1, HAS_LOGICAL=1, HAS_CMP=1, HAS_MUX=1

module processing_element_NESW
  import cgra_pkg::*;
#(
  parameter int             DATA_WIDTH    = 32,
  parameter config_border_t CONFIG_BORDER = NORTH,
  // FU operation enables
  parameter bit             HAS_ADDSUB    = 1,
  parameter bit             HAS_MUL       = 1,
  parameter bit             HAS_SHIFT     = 1,
  parameter bit             HAS_LOGICAL   = 1,
  // FU feature enables
  parameter bit             HAS_CMP       = 1,
  parameter bit             HAS_MUX       = 1
) (
  // Clock and reset
  input logic clk_i,
  input logic rst_ni,
  input logic clr_i,

  // Configuration chain
  input  logic conf_en_i,
  output logic conf_en_o,

  // Input data - NESW
  input  logic [DATA_WIDTH-1:0] north_din_i,
  input  logic                  north_din_v_i,
  output logic                  north_din_r_o,
  input  logic [DATA_WIDTH-1:0] east_din_i,
  input  logic                  east_din_v_i,
  output logic                  east_din_r_o,
  input  logic [DATA_WIDTH-1:0] south_din_i,
  input  logic                  south_din_v_i,
  output logic                  south_din_r_o,
  input  logic [DATA_WIDTH-1:0] west_din_i,
  input  logic                  west_din_v_i,
  output logic                  west_din_r_o,

  // Output data - NESW
  output logic [DATA_WIDTH-1:0] north_dout_o,
  output logic                  north_dout_v_o,
  input  logic                  north_dout_r_i,
  output logic [DATA_WIDTH-1:0] east_dout_o,
  output logic                  east_dout_v_o,
  input  logic                  east_dout_r_i,
  output logic [DATA_WIDTH-1:0] south_dout_o,
  output logic                  south_dout_v_o,
  input  logic                  south_dout_r_i,
  output logic [DATA_WIDTH-1:0] west_dout_o,
  output logic                  west_dout_v_o,
  input  logic                  west_dout_r_i
);
  // synopsys sync_set_reset clr_i

  localparam real CONF_SIZE_BITS = 160.0;
  localparam int CONF_WORDS = int'($ceil(CONF_SIZE_BITS / DATA_WIDTH)); // 32-bit version of STRELA uses five 32-bit words for config, 64-bit version uses three 64-bit words
  localparam int CONF_WIRE_BITS = CONF_WORDS * DATA_WIDTH;

  // ---------------------------------------------- //
  //                 CONFIGURATION                  //
  // ---------------------------------------------- //

  // PE routing
  logic [           2:0] mux_sel_n;
  logic [           2:0] mux_sel_e;
  logic [           2:0] mux_sel_s;
  logic [           2:0] mux_sel_w;
  logic [           1:0] data_mux_sel_n;
  logic [           1:0] data_mux_sel_e;
  logic [           1:0] data_mux_sel_s;
  logic [           1:0] data_mux_sel_w;
  logic [           5:0] mask_fs_n;
  logic [           5:0] mask_fs_e;
  logic [           5:0] mask_fs_s;
  logic [           5:0] mask_fs_w;
  logic                  eb_n_en;
  logic                  eb_e_en;
  logic                  eb_s_en;
  logic                  eb_w_en;

  // Data path
  logic                  eb_fu1_en;
  logic                  eb_fu2_en;
  logic [           2:0] mux_sel_1;
  logic [           2:0] mux_sel_2;
  logic [           1:0] mux_sel_c;
  logic [           1:0] jm_mode;
  logic                  feedback;
  logic [           2:0] alu_sel;
  logic                  cmp_sel;
  logic [           1:0] out_sel;
  logic [           5:0] mask_fs_fu;
  logic                  initial_valid;
  logic [          15:0] delay_value;
  logic [DATA_WIDTH-1:0] initial_data;
  logic [DATA_WIDTH-1:0] constant;

  // Config shift register
  logic [CONF_WIRE_BITS-1:0] conf_wire;
  logic [CONF_WIRE_BITS-1:0] conf_reg_ext;
  logic [             159:0] conf_reg;

  // Temp wires for CONFIG_BORDER routing
  logic [DATA_WIDTH-1:0] tmp_north_dout;
  logic [DATA_WIDTH-1:0] tmp_east_dout;
  logic [DATA_WIDTH-1:0] tmp_south_dout;
  logic [DATA_WIDTH-1:0] tmp_west_dout;
  logic                  tmp_north_din_v;
  logic                  tmp_east_din_v;
  logic                  tmp_south_din_v;
  logic                  tmp_west_din_v;

  // ---------------------------------------------- //
  //               INTERCONNECT SIGNALS             //
  // ---------------------------------------------- //

  // NESW input elastic buffers
  logic [DATA_WIDTH-1:0] north_buffer;
  logic [DATA_WIDTH-1:0] east_buffer;
  logic [DATA_WIDTH-1:0] south_buffer;
  logic [DATA_WIDTH-1:0] west_buffer;
  logic                  north_buffer_v;
  logic                  east_buffer_v;
  logic                  south_buffer_v;
  logic                  west_buffer_v;
  logic                  temp_north_buffer_v;
  logic                  temp_east_buffer_v;
  logic                  temp_south_buffer_v;
  logic                  temp_west_buffer_v;
  logic                  north_buffer_r;
  logic                  east_buffer_r;
  logic                  south_buffer_r;
  logic                  west_buffer_r;

  // Cell input path
  logic [DATA_WIDTH-1:0] EB_din_1;
  logic [DATA_WIDTH-1:0] EB_din_2;
  logic                  EB_din_1_v;
  logic                  EB_din_2_v;
  logic [DATA_WIDTH-1:0] jm_din_1;
  logic [DATA_WIDTH-1:0] jm_din_2;
  logic                  jm_din_1_v;
  logic                  jm_din_1_r;
  logic                  jm_din_2_v;
  logic                  jm_din_2_r;
  logic                  jm_cin;
  logic                  jm_cin_v;
  logic                  jm_cout;
  logic [DATA_WIDTH-1:0] jm_dout_1;
  logic [DATA_WIDTH-1:0] jm_dout_2;
  logic                  jm_dout_v;

  // Cell readys
  logic                  din_1_r;
  logic                  din_2_r;
  logic                  cin_r;
  logic                  dout_r;

  // FU outputs
  logic [DATA_WIDTH-1:0] dout;
  logic                  dout_v;
  logic                  dout_d_v;
  logic                  dout_b1_v;
  logic                  dout_b2_v;

  // ---------------------------------------------- //
  //              CONFIG SHIFT REGISTER             //
  // ---------------------------------------------- //

  generate
    if (CONFIG_BORDER == NORTH) begin : gen_north_conf
      assign conf_wire       = {north_din_i, conf_reg_ext[CONF_WIRE_BITS-1:DATA_WIDTH]};
      assign tmp_north_din_v = north_din_v_i && !conf_en_i;
      assign tmp_east_din_v  = east_din_v_i;
      assign tmp_south_din_v = south_din_v_i;
      assign tmp_west_din_v  = west_din_v_i;
      assign north_dout_o    = tmp_north_dout;
      assign east_dout_o     = tmp_east_dout;
      assign south_dout_o    = conf_en_i ? conf_reg_ext[DATA_WIDTH-1:0] : tmp_south_dout;
      assign west_dout_o     = tmp_west_dout;
    end else if (CONFIG_BORDER == EAST) begin : gen_east_conf
      assign conf_wire       = {east_din_i, conf_reg_ext[CONF_WIRE_BITS-1:DATA_WIDTH]};
      assign tmp_north_din_v = north_din_v_i;
      assign tmp_east_din_v  = east_din_v_i && !conf_en_i;
      assign tmp_south_din_v = south_din_v_i;
      assign tmp_west_din_v  = west_din_v_i;
      assign north_dout_o    = tmp_north_dout;
      assign east_dout_o     = tmp_east_dout;
      assign south_dout_o    = tmp_south_dout;
      assign west_dout_o     = conf_en_i ? conf_reg_ext[DATA_WIDTH-1:0] : tmp_west_dout;
    end else if (CONFIG_BORDER == SOUTH) begin : gen_south_conf
      assign conf_wire       = {south_din_i, conf_reg_ext[CONF_WIRE_BITS-1:DATA_WIDTH]};
      assign tmp_north_din_v = north_din_v_i;
      assign tmp_east_din_v  = east_din_v_i;
      assign tmp_south_din_v = south_din_v_i && !conf_en_i;
      assign tmp_west_din_v  = west_din_v_i;
      assign north_dout_o    = conf_en_i ? conf_reg_ext[DATA_WIDTH-1:0] : tmp_north_dout;
      assign east_dout_o     = tmp_east_dout;
      assign south_dout_o    = tmp_south_dout;
      assign west_dout_o     = tmp_west_dout;
    end else begin : gen_west_conf
      assign conf_wire       = {west_din_i, conf_reg_ext[CONF_WIRE_BITS-1:DATA_WIDTH]};
      assign tmp_north_din_v = north_din_v_i;
      assign tmp_east_din_v  = east_din_v_i;
      assign tmp_south_din_v = south_din_v_i;
      assign tmp_west_din_v  = west_din_v_i && !conf_en_i;
      assign north_dout_o    = tmp_north_dout;
      assign east_dout_o     = conf_en_i ? conf_reg_ext[DATA_WIDTH-1:0] : tmp_east_dout;
      assign south_dout_o    = tmp_south_dout;
      assign west_dout_o     = tmp_west_dout;
    end
  endgenerate

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      conf_reg_ext <= '0;
    end else begin
      if (conf_en_i) begin
        conf_reg_ext <= conf_wire;
      end
    end
  end

  assign conf_en_o      = conf_en_i;
  assign conf_reg       = conf_reg_ext[CONF_WIRE_BITS-1:DATA_WIDTH-32];

  // ---------------------------------------------- //
  //               CONFIG DECODING                  //
  // ---------------------------------------------- //

  // PE routing
  assign eb_n_en        = conf_en_i ? 1'b0 : conf_reg[0];
  assign eb_e_en        = conf_en_i ? 1'b0 : conf_reg[1];
  assign eb_s_en        = conf_en_i ? 1'b0 : conf_reg[2];
  assign eb_w_en        = conf_en_i ? 1'b0 : conf_reg[3];
  assign mask_fs_n      = conf_reg[9:4];
  assign mask_fs_e      = conf_reg[15:10];
  assign mask_fs_s      = conf_reg[21:16];
  assign mask_fs_w      = conf_reg[27:22];
  // RESERVED [33:28]
  assign mux_sel_n      = conf_reg[36:34];
  assign mux_sel_e      = conf_reg[39:37];
  assign mux_sel_s      = conf_reg[42:40];
  assign mux_sel_w      = conf_reg[45:43];
  // RESERVED [49:46]

  // Data path
  assign eb_fu1_en      = conf_reg[50];
  assign eb_fu2_en      = conf_reg[51];
  assign mux_sel_1      = conf_reg[54:52];
  assign mux_sel_2      = conf_reg[57:55];
  assign mux_sel_c      = conf_reg[59:58];
  // RESERVED [60]
  assign jm_mode        = conf_reg[62:61];
  assign feedback       = conf_reg[63];
  assign alu_sel        = conf_reg[66:64];
  assign cmp_sel        = conf_reg[67];
  assign out_sel        = conf_reg[69:68];
  assign mask_fs_fu     = conf_reg[75:70];
  // RESERVED [77:76]
  assign initial_valid  = conf_reg[78];
  // RESERVED [79]
  assign delay_value    = conf_reg[95:80];
  assign initial_data   = DATA_WIDTH'(signed'(conf_reg[127:96]));
  assign constant       = DATA_WIDTH'(signed'(conf_reg[159:128]));

  // Data output mux sel: mux_sel[2]=1 => FU output (index 3), else use [1:0]
  assign data_mux_sel_n = mux_sel_n[2] ? 2'b11 : mux_sel_n[1:0];
  assign data_mux_sel_e = mux_sel_e[2] ? 2'b11 : mux_sel_e[1:0];
  assign data_mux_sel_s = mux_sel_s[2] ? 2'b11 : mux_sel_s[1:0];
  assign data_mux_sel_w = mux_sel_w[2] ? 2'b11 : mux_sel_w[1:0];

  /* ------------------------------ NORTH NODE ------------------------------- */

  elastic_buffer #(
    .DATA_WIDTH(DATA_WIDTH)
  ) REG_N (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),
    .clr_i   (clr_i),
    .en_i    (eb_n_en),
    .din_i   (north_din_i),
    .din_v_i (tmp_north_din_v),
    .din_r_o (north_din_r_o),
    .dout_o  (north_buffer),
    .dout_v_o(temp_north_buffer_v),
    .dout_r_i(north_buffer_r)
  );

  assign north_buffer_v = temp_north_buffer_v && north_buffer_r;

  fork_sender #(
    .NUM_READYS(6)
  ) FS_N (
    .fork_mask_i (mask_fs_n),
    .ready_in_o  (north_buffer_r),
    .readys_out_i({din_1_r, din_2_r, cin_r, east_dout_r_i, south_dout_r_i, west_dout_r_i})
  );

  // Output - data mux
  mux #(
    .NUM_INPUTS(4),
    .DATA_WIDTH(DATA_WIDTH)
  ) MUX_N (
    .sel_i(data_mux_sel_n),
    .mux_i({dout, west_buffer, south_buffer, east_buffer}),
    .mux_o(tmp_north_dout)
  );

  // Output - valid mux (7 options: 3 neighbor buffers, dout_v, dout_d_v, dout_b1_v, dout_b2_v)
  mux #(
    .NUM_INPUTS(7),
    .DATA_WIDTH(1)
  ) MUX_N_v (
    .sel_i(mux_sel_n),
    .mux_i({dout_b2_v, dout_b1_v, dout_d_v, dout_v, west_buffer_v, south_buffer_v, east_buffer_v}),
    .mux_o(north_dout_v_o)
  );

  /* ------------------------------ EAST  NODE ------------------------------- */

  elastic_buffer #(
    .DATA_WIDTH(DATA_WIDTH)
  ) REG_E (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),
    .clr_i   (clr_i),
    .en_i    (eb_e_en),
    .din_i   (east_din_i),
    .din_v_i (tmp_east_din_v),
    .din_r_o (east_din_r_o),
    .dout_o  (east_buffer),
    .dout_v_o(temp_east_buffer_v),
    .dout_r_i(east_buffer_r)
  );

  assign east_buffer_v = temp_east_buffer_v && east_buffer_r;

  fork_sender #(
    .NUM_READYS(6)
  ) FS_E (
    .fork_mask_i (mask_fs_e),
    .ready_in_o  (east_buffer_r),
    .readys_out_i({din_1_r, din_2_r, cin_r, north_dout_r_i, south_dout_r_i, west_dout_r_i})
  );

  // Output - data mux
  mux #(
    .NUM_INPUTS(4),
    .DATA_WIDTH(DATA_WIDTH)
  ) MUX_E (
    .sel_i(data_mux_sel_e),
    .mux_i({dout, west_buffer, south_buffer, north_buffer}),
    .mux_o(tmp_east_dout)
  );

  // Output - valid mux
  mux #(
    .NUM_INPUTS(7),
    .DATA_WIDTH(1)
  ) MUX_E_v (
    .sel_i(mux_sel_e),
    .mux_i({dout_b2_v, dout_b1_v, dout_d_v, dout_v, west_buffer_v, south_buffer_v, north_buffer_v}),
    .mux_o(east_dout_v_o)
  );

  /* ------------------------------ SOUTH NODE ------------------------------- */

  elastic_buffer #(
    .DATA_WIDTH(DATA_WIDTH)
  ) REG_S (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),
    .clr_i   (clr_i),
    .en_i    (eb_s_en),
    .din_i   (south_din_i),
    .din_v_i (tmp_south_din_v),
    .din_r_o (south_din_r_o),
    .dout_o  (south_buffer),
    .dout_v_o(temp_south_buffer_v),
    .dout_r_i(south_buffer_r)
  );

  assign south_buffer_v = temp_south_buffer_v && south_buffer_r;

  fork_sender #(
    .NUM_READYS(6)
  ) FS_S (
    .fork_mask_i (mask_fs_s),
    .ready_in_o  (south_buffer_r),
    .readys_out_i({din_1_r, din_2_r, cin_r, north_dout_r_i, east_dout_r_i, west_dout_r_i})
  );

  // Output - data mux
  mux #(
    .NUM_INPUTS(4),
    .DATA_WIDTH(DATA_WIDTH)
  ) MUX_S (
    .sel_i(data_mux_sel_s),
    .mux_i({dout, west_buffer, east_buffer, north_buffer}),
    .mux_o(tmp_south_dout)
  );

  // Output - valid mux
  mux #(
    .NUM_INPUTS(7),
    .DATA_WIDTH(1)
  ) MUX_S_v (
    .sel_i(mux_sel_s),
    .mux_i({dout_b2_v, dout_b1_v, dout_d_v, dout_v, west_buffer_v, east_buffer_v, north_buffer_v}),
    .mux_o(south_dout_v_o)
  );

  /* ------------------------------ WEST  NODE ------------------------------- */

  elastic_buffer #(
    .DATA_WIDTH(DATA_WIDTH)
  ) REG_W (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),
    .clr_i   (clr_i),
    .en_i    (eb_w_en),
    .din_i   (west_din_i),
    .din_v_i (tmp_west_din_v),
    .din_r_o (west_din_r_o),
    .dout_o  (west_buffer),
    .dout_v_o(temp_west_buffer_v),
    .dout_r_i(west_buffer_r)
  );

  assign west_buffer_v = temp_west_buffer_v && west_buffer_r;

  fork_sender #(
    .NUM_READYS(6)
  ) FS_W (
    .fork_mask_i (mask_fs_w),
    .ready_in_o  (west_buffer_r),
    .readys_out_i({din_1_r, din_2_r, cin_r, north_dout_r_i, east_dout_r_i, south_dout_r_i})
  );

  // Output - data mux
  mux #(
    .NUM_INPUTS(4),
    .DATA_WIDTH(DATA_WIDTH)
  ) MUX_W (
    .sel_i(data_mux_sel_w),
    .mux_i({dout, south_buffer, east_buffer, north_buffer}),
    .mux_o(tmp_west_dout)
  );

  // Output - valid mux
  mux #(
    .NUM_INPUTS(7),
    .DATA_WIDTH(1)
  ) MUX_W_v (
    .sel_i(mux_sel_w),
    .mux_i({dout_b2_v, dout_b1_v, dout_d_v, dout_v, south_buffer_v, east_buffer_v, north_buffer_v}),
    .mux_o(west_dout_v_o)
  );

  /* ------------------------------ DATA PATH -------------------------------- */

  // ---- Input 1 ----
  // Source: 0=N 1=E 2=S 3=W 4=constant 5=dout(feedback)
  mux #(
    .NUM_INPUTS(6),
    .DATA_WIDTH(DATA_WIDTH)
  ) MUX_1 (
    .sel_i(mux_sel_1),
    .mux_i({dout, constant, west_din_i, south_din_i, east_din_i, north_din_i}),
    .mux_o(EB_din_1)
  );

  mux #(
    .NUM_INPUTS(6),
    .DATA_WIDTH(1)
  ) MUX_1_v (
    .sel_i(mux_sel_1),
    .mux_i({dout_v, 1'b1, west_din_v_i, south_din_v_i, east_din_v_i, north_din_v_i}),
    .mux_o(EB_din_1_v)
  );

  elastic_buffer #(
    .DATA_WIDTH(DATA_WIDTH)
  ) REG_1 (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),
    .clr_i   (clr_i),
    .en_i    (eb_fu1_en),
    .din_i   (EB_din_1),
    .din_v_i (EB_din_1_v),
    .din_r_o (din_1_r),
    .dout_o  (jm_din_1),
    .dout_v_o(jm_din_1_v),
    .dout_r_i(jm_din_1_r)
  );

  // ---- Input 2 ----
  mux #(
    .NUM_INPUTS(6),
    .DATA_WIDTH(DATA_WIDTH)
  ) MUX_2 (
    .sel_i(mux_sel_2),
    .mux_i({dout, constant, west_din_i, south_din_i, east_din_i, north_din_i}),
    .mux_o(EB_din_2)
  );

  mux #(
    .NUM_INPUTS(6),
    .DATA_WIDTH(1)
  ) MUX_2_v (
    .sel_i(mux_sel_2),
    .mux_i({dout_v, 1'b1, west_din_v_i, south_din_v_i, east_din_v_i, north_din_v_i}),
    .mux_o(EB_din_2_v)
  );

  elastic_buffer #(
    .DATA_WIDTH(DATA_WIDTH)
  ) REG_2 (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),
    .clr_i   (clr_i),
    .en_i    (eb_fu2_en),
    .din_i   (EB_din_2),
    .din_v_i (EB_din_2_v),
    .din_r_o (din_2_r),
    .dout_o  (jm_din_2),
    .dout_v_o(jm_din_2_v),
    .dout_r_i(jm_din_2_r)
  );

  // ---- Control (cin) - generate only this path ----
  generate
    if (HAS_MUX) begin : gen_cin
      // Source: 0=N 1=E 2=S 3=W (bit[0] of each direction's buffer)
      mux #(
        .NUM_INPUTS(4),
        .DATA_WIDTH(1)
      ) MUX_C (
        .sel_i(mux_sel_c),
        .mux_i({west_din_i[0], south_din_i[0], east_din_i[0], north_din_i[0]}),
        .mux_o(jm_cin)
      );

      mux #(
        .NUM_INPUTS(4),
        .DATA_WIDTH(1)
      ) MUX_C_v (
        .sel_i(mux_sel_c),
        .mux_i({west_din_v_i, south_din_v_i, east_din_v_i, north_din_v_i}),
        .mux_o(jm_cin_v)
      );
    end else begin : gen_no_cin
      assign jm_cin   = 1'b0;
      assign jm_cin_v = 1'b1;
    end
  endgenerate

  // ---- Join/Merge ----
  join_merge #(
    .DATA_WIDTH(DATA_WIDTH)
  ) join_merge_inst (
    .mode_i   (jm_mode),
    .din_1_i  (jm_din_1),
    .din_1_v_i(jm_din_1_v),
    .din_1_r_o(jm_din_1_r),
    .din_2_i  (jm_din_2),
    .din_2_v_i(jm_din_2_v),
    .din_2_r_o(jm_din_2_r),
    .cin_i    (jm_cin),
    .cin_v_i  (jm_cin_v),
    .cin_r_o  (cin_r),
    .dout_1_o (jm_dout_1),
    .dout_2_o (jm_dout_2),
    .cout_o   (jm_cout),
    .out_v_o  (jm_dout_v),
    .out_r_i  (dout_r)
  );

  /* ------------------------------ FUNCTIONAL UNIT -------------------------- */

  functional_unit #(
    .DATA_WIDTH    (DATA_WIDTH),
    .N_DESTINATIONS(6),
    .HAS_ADDSUB    (HAS_ADDSUB),
    .HAS_MUL       (HAS_MUL),
    .HAS_SHIFT     (HAS_SHIFT),
    .HAS_LOGICAL   (HAS_LOGICAL),
    .HAS_CMP       (HAS_CMP),
    .HAS_MUX       (HAS_MUX)
  ) FU_inst (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .clr_i(clr_i),
    .initial_data_i(initial_data),
    .initial_valid_i(initial_valid),
    .feedback_i(feedback),
    .alu_sel_i(alu_sel),
    .cmp_sel_i(cmp_sel),
    .out_sel_i(out_sel),
    .delay_value_i(delay_value),
    .fork_mask_i(mask_fs_fu),
    .din_1_i(jm_dout_1),
    .din_2_i(jm_dout_2),
    .cin_i(jm_cout),
    .dout_o(dout),
    .in_v_i(jm_dout_v),
    .in_r_o(dout_r),
    .out_v_o(dout_v),
    .out_d_v_o(dout_d_v),
    .out_b1_v_o(dout_b1_v),
    .out_b2_v_o(dout_b2_v),
    .out_r_i({din_2_r, din_1_r, north_dout_r_i, east_dout_r_i, south_dout_r_i, west_dout_r_i})
  );

endmodule
