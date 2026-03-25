// Copyright 2025 CEI-UPM
// Solderpad Hardware License, Version 2.1, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Daniel Vazquez (daniel.vazquez@upm.es)

module adder_substracter #(
  parameter int DATA_WIDTH = 32
) (
  input logic [DATA_WIDTH-1:0] a_i,
  input logic [DATA_WIDTH-1:0] b_i,
  input logic addsub_mode_i,
  output logic [DATA_WIDTH-1:0] res_o
);

  DW01_addsub #(
    .width(DATA_WIDTH)
  ) U1 (
    .A(a_i),
    .B(b_i),
    .CI(1'b0),
    .ADD_SUB(addsub_mode_i),
    .SUM(res_o),
    .CO()
  );

endmodule
