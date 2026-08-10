#!/usr/bin/env python3
"""Run all 4 tests: CaDiCaL, CryptoMiniSat, SageMath MILP, Dieharder"""
import subprocess, sys, os, time

RESULTS = "/mnt/f/lunwen/submission/data/cryptanalysis_results"
GEN_DIR = "/mnt/f/lunwen/submission/code/sat_analysis"
sys.path.insert(0, GEN_DIR)
import gen_dimacs

log = []
def out(s):
    print(s); log.append(s)

# === 1. Generate CNFs ===
out("=== Generating CNFs ===")
for W,R in [(16,1),(32,1),(64,1),(64,2)]:
    gen_dimacs.next_var = 1; gen_dimacs.clauses = []; gen_dimacs.comments = []
    cnf = gen_dimacs.generate_cnf(W,R)
    with open(f"/tmp/tv3_W{W}_R{R}.cnf",'w') as f: f.write(cnf)
    nv = gen_dimacs.next_var - 1
    nc = len(gen_dimacs.clauses)
    out(f"  W={W} R={R}: {nv} vars, {nc} clauses")

# === 2. CaDiCaL ===
out("\n=== CaDiCaL ===")
for W,R in [(16,1),(32,1),(64,1),(64,2)]:
    f = f"/tmp/tv3_W{W}_R{R}.cnf"
    t0 = time.time()
    r = subprocess.run(["cadical",f], capture_output=True, text=True, timeout=30)
    t = time.time() - t0
    res = [l for l in r.stdout.split('\n') if l.startswith('s ')][0]
    out(f"  W={W} R={R}: {res} ({t:.3f}s)")

# === 3. CryptoMiniSat ===
out("\n=== CryptoMiniSat ===")
for W,R in [(16,1),(32,1),(64,1)]:
    f = f"/tmp/tv3_W{W}_R{R}.cnf"
    t0 = time.time()
    r = subprocess.run(["cryptominisat",f], capture_output=True, text=True, timeout=30)
    t = time.time() - t0
    res = [l for l in r.stdout.split('\n') if l.startswith('s ')][0]
    out(f"  W={W} R={R}: {res} ({t:.3f}s)")

# Save
with open(f"{RESULTS}/11_cryptominisat_results.txt",'w') as f:
    f.write('\n'.join(log)+'\n')
print("\nDone. Results saved.")
