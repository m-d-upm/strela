// Copyright 2025 CEI-UPM
// Solderpad Hardware License, Version 2.1, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Daniel Vazquez (daniel.vazquez@upm.es)

module multiplier_pe #(
  parameter int DATA_WIDTH = 32
) (
  input  logic signed [DATA_WIDTH-1:0] a_i,
  input  logic signed [DATA_WIDTH-1:0] b_i,
  output logic signed [DATA_WIDTH-1:0] res_o
);

  logic signed [DATA_WIDTH/2-1:0] a, b;
  assign a = a_i[DATA_WIDTH/2-1:0];
  assign b = b_i[DATA_WIDTH/2-1:0];

  DW02_mult #(
    .A_width(DATA_WIDTH / 2),
    .B_width(DATA_WIDTH / 2)
  ) U1 (
    .A(a),
    .B(b),
    .TC(1'b1),
    .PRODUCT(res_o)
  );

endmodule
