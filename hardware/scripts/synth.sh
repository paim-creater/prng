#!/bin/bash
#=============================================================================
# Tempest v3 FPGA Synthesis Script
# Uses open-source Yosys + nextpnr for Lattice iCE40 FPGAs
#=============================================================================

set -e

TOP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RTL_DIR="$TOP_DIR/rtl"
BUILD_DIR="$TOP_DIR/build"
DEVICE="hx8k"  # iCE40 HX8K (iCEBreaker), use "up5k" for iCE40UP5K

mkdir -p "$BUILD_DIR"

echo "=== Tempest v3 FPGA Synthesis ==="
echo "Device: iCE40 $DEVICE"
echo ""

# Step 1: Synthesize Verilog to JSON netlist
echo "[1/3] Yosys synthesis..."
yosys -p "
    read -sv $RTL_DIR/andmix4.v
    read -sv $RTL_DIR/round_function.v
    read -sv $RTL_DIR/output_function.v
    read -sv $RTL_DIR/tempest_v3_top.v
    synth_ice40 -top tempest_v3_top -json $BUILD_DIR/tempest_v3.json
" 2>&1 | tee $BUILD_DIR/synth.log

# Step 2: Place and route
echo "[2/3] nextpnr place-and-route..."
nextpnr-ice40 --$DEVICE \
    --json $BUILD_DIR/tempest_v3.json \
    --pcf $TOP_DIR/constraints/tempest_v3.pcf \
    --asc $BUILD_DIR/tempest_v3.asc \
    --freq 48 \
    2>&1 | tee $BUILD_DIR/pnr.log

# Step 3: Generate bitstream
echo "[3/3] Bitstream generation..."
icepack $BUILD_DIR/tempest_v3.asc $BUILD_DIR/tempest_v3.bin

echo ""
echo "=== Done ==="
echo "Bitstream: $BUILD_DIR/tempest_v3.bin"
echo "Resource usage:"
grep -E "ICEs|LUT|DFF|BRAM|IO" $BUILD_DIR/pnr.log | head -20
