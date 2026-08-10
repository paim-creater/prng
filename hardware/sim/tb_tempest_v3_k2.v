//=============================================================================
// tb_tempest_v3.v — KAT verification of the Tempest v3 (Algorithm 1) RTL
// against the C ground truth (github_release/src/tempest_v3.c).
//
// Key = [1,2,3,4], nonce = [5,6], loaded as three 128-bit words
// (load_sel 0: k0k1 = 1,2 ; 1: k2k3 = 3,4 ; 2: n0n1 = 5,6).
// Expected single-word outputs (from the verified Python port of the C):
//   6BBE30BB1D12DDD0, B9167FE6CCEC68D9, CF6F7BA5C6AED360,
//   A53C77D6D081BEC3, 7F5A13D9CBF1CD84   (word 1 = the published KAT)
//=============================================================================
`timescale 1ns/1ps

module tb_tempest_v3;   // K2 variant expectations
    reg         clk = 0;
    reg         rst_n = 0;
    reg         en = 0;
    reg  [127:0] key_word = 128'd0;
    reg  [1:0]  load_sel = 2'd0;
    wire [63:0]  rnd_data;
    wire        rnd_valid;
    wire        busy;

    tempest_v3_top dut (
        .clk(clk), .rst_n(rst_n), .en(en),
        .key_word(key_word), .load_sel(load_sel),
        .rnd_data(rnd_data), .rnd_valid(rnd_valid), .busy(busy)
    );

    always #5 clk = ~clk;   // 100 MHz

    integer words = 0;
    integer errors = 0;
    reg [63:0] exp [1:5];
    integer wi;
    initial begin
        exp[1] = 64'h8CFA777E174BC028;
        exp[2] = 64'h21AC9AFAF037A2B6;
        exp[3] = 64'h269AA567790CFADC;
        exp[4] = 64'h14D57F6D1444E54C;
        exp[5] = 64'h09A58C0790886BF2;
    end

    always @(posedge clk) begin
        if (rnd_valid) begin
            words = words + 1;
            if (words <= 5) begin
                if (rnd_data !== exp[words]) begin
                    errors = errors + 1;
                    $display("FAIL word %0d: got %016h want %016h",
                             words, rnd_data, exp[words]);
                end else begin
                    $display("PASS word %0d: %016h", words, rnd_data);
                end
            end
            if (words == 5) begin
                if (errors == 0) $display("KAT PASS (5 words)");
                else $display("KAT FAIL (%0d errors)", errors);
                $finish;
            end
        end
    end

    // Clock edges at 5,15,25,... ns. en at t=30 → IDLE sees it at t=35 →
    // LOAD executes at t=45. Each load_sel group must be stable at its
    // consuming edge: sel=0 at t=45, sel=1 at t=55, sel=2 at t=65.
    // Clock edges at 5,15,25,...; k0k1 are captured by IDLE (key_word is
    // held before en). LOAD consumes one group per edge: sel=0 (k2k3) at
    // t=45, sel=1 (n0n1) at t=55 (→ INIT). Each group is swapped 1 ns
    // AFTER its consuming edge (t=46), so the next edge reads the next
    // group with no race.
    initial begin
        #20 rst_n = 1;
        key_word = 128'h0000000000000002_0000000000000001;  // k0k1 = (1,2)
        load_sel = 2'd0;
        #10 en = 1;                    // t=30: IDLE captures k0k1 at t=35
        #16                            // t=46: sel=0 consumed at t=45
        key_word = 128'h0000000000000004_0000000000000003;  // k2k3 = (3,4)
        load_sel = 2'd0;
        #10                            // t=56: sel=1 consumed at t=55
        key_word = 128'h0000000000000006_0000000000000005;  // n0n1 = (5,6)
        load_sel = 2'd1;
        #10                            // t=66: LOAD done at t=65
        en = 0;
        #10000;
        $display("TIMEOUT — no output within 10 us");
        $finish;
    end

    initial begin
        $dumpfile("tempest_v3.vcd");
        $dumpvars(0, tb_tempest_v3);
    end

    // debug: dump every LOAD cycle
    always @(posedge clk) begin
        if (dut.state == 3'd1) begin
            $display("LOAD t=%0t load_cnt=%0d sel=%0d kw=%016h%016h u=%016h v=%016h w=%016h z=%016h",
                     $time, dut.load_cnt, load_sel, key_word[127:64], key_word[63:0],
                     dut.u, dut.v, dut.w, dut.z);
        end
    end

    // debug: dump state words right after LOAD completes (first INIT cycle)
    reg [2:0] prev_state;
    always @(posedge clk) prev_state <= dut.state;
    always @(posedge clk) begin
        if (dut.state == 3'd2 && prev_state != 3'd2) begin  // entered INIT
            $display("INIT start: u=%016h v=%016h w=%016h z=%016h rk_u=%016h rkey=%016h",
                     dut.u, dut.v, dut.w, dut.z, dut.rk_u, dut.round_key);
        end
    end

endmodule
