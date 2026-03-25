module DW01_ash #(
    parameter int A_width  = 32,
    parameter int SH_width = 6
)(
    input  logic [A_width-1:0]  A,
    input  logic                DATA_TC,
    input  logic [SH_width-1:0] SH,
    input  logic                SH_TC,
    output logic [A_width-1:0]  B
);

    // Direction: shift right when SH is signed (SH_TC=1) and negative
    logic dir_right;
    assign dir_right = SH_TC && SH[SH_width-1];

    // Shift magnitude (unsigned), one extra bit to cover full range
    logic [SH_width:0] sh_mag_raw;
    logic [SH_width:0] sh_mag;

    always_comb begin
        if (SH_TC && SH[SH_width-1])
            // Two's complement negation: explicit ~+1 avoids int cast issues
            sh_mag_raw = (SH_width+1)'(~SH) + (SH_width+1)'(1);
        else
            sh_mag_raw = (SH_width+1)'(SH);
    end

    always_comb begin
        if (sh_mag_raw >= (SH_width+1)'(A_width))
            sh_mag = (SH_width+1)'(A_width);
        else
            sh_mag = sh_mag_raw;
    end

    // Arithmetic right shift kept as signed so >>> sign-extends correctly
    logic signed [A_width-1:0] arith_shift_right;
    assign arith_shift_right = $signed(A) >>> sh_mag;

    always_comb begin
        if (dir_right) begin
            if (DATA_TC)
                B = (sh_mag >= (SH_width+1)'(A_width)) ? {A_width{A[A_width-1]}} : arith_shift_right;
            else
                B = (sh_mag >= (SH_width+1)'(A_width)) ? '0 : A >> sh_mag;
        end else begin
            B = (sh_mag >= (SH_width+1)'(A_width)) ? '0 : A << sh_mag;
        end
    end

endmodule
