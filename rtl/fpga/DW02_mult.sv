module DW02_mult #(
    parameter int A_width = 16,
    parameter int B_width = 16
)(
    input  logic [A_width-1:0] A,
    input  logic [B_width-1:0] B,
    input  logic        TC,
    output logic [A_width+B_width-1:0] PRODUCT
);
    logic signed [A_width+B_width-1:0] product_signed;
    logic        [A_width+B_width-1:0] product_unsigned;

    assign product_signed   = $signed(A) * $signed(B);
    assign product_unsigned = A * B;

    assign PRODUCT = TC ? product_signed : product_unsigned;

endmodule
