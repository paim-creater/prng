#!/usr/bin/env python3
"""验证 andmix4 的 SAT 编码是否正确"""
import sys; sys.path.insert(0, '.')
from pysat.solvers import Glucose3
import gen_dimacs
import time

W = 64

# C 参考: andmix4(1)
def andmix4_ref(t):
    for r1,r2 in [(31,53),(17,43),(7,23),(5,19)]:
        t ^= (((t<<r1)|(t>>(W-r1)))&((1<<W)-1)) & (((t<<r2)|(t>>(W-r2)))&((1<<W)-1))
    return t & ((1<<W)-1)

expected = andmix4_ref(1)
print(f"C reference: andmix4(1) = {expected:016x}")

# 创建 SAT 编码: t=1 → andmix4(t) → 验证输出匹配 expected
gen_dimacs.next_var = 1; gen_dimacs.clauses = []; gen_dimacs.comments = []

# 输入变量
t_in = gen_dimacs.Word.new(W)

# 约束 t_in = 1
for i in range(W):
    bit = (1>>i)&1
    gen_dimacs.clauses.append([t_in.bits[i]] if bit else [-t_in.bits[i]])

# 计算 andmix4
t_mixed = gen_dimacs.andmix4(t_in, W)

# 约束 t_mixed = expected
for i in range(W):
    bit = (expected>>i)&1
    gen_dimacs.clauses.append([t_mixed.bits[i]] if bit else [-t_mixed.bits[i]])

nvars = gen_dimacs.next_var - 1
print(f"SAT encoding: {nvars} vars, {len(gen_dimacs.clauses)} clauses")

g = Glucose3()
for c in gen_dimacs.clauses: g.add_clause(c)
t0 = time.time()
res = g.solve()
t = time.time() - t0
print(f"Result: {'SAT' if res else 'UNSAT'} ({t:.3f}s)")

if res:
    print("andmix4 encoding: CORRECT")
else:
    print("andmix4 encoding: WRONG - doesn't match C reference")

    # 调试: 只检查第一级
    print("\nDebugging stage by stage...")
    for stage in range(4):
        rots = [(31,53),(17,43),(7,23),(5,19)]
        gen_dimacs2 = __import__('gen_dimacs', fromlist=[''])
        gen_dimacs2.next_var = 1
        gen_dimacs2.clauses = []

        t_in2 = gen_dimacs2.Word.new(W)
        for i in range(W):
            gen_dimacs2.clauses.append([t_in2.bits[i]] if (1>>i)&1 else [-t_in2.bits[i]])

        cur = t_in2.copy()
        for s in range(stage+1):
            r1,r2 = rots[s]
            tr1 = cur.rotl(r1, W)
            tr2 = cur.rotl(r2, W)
            a = tr1.and_word(tr2, W)
            cur = cur.xor(a, W)

        # 计算 C 参考值
        ct = 1
        for s in range(stage+1):
            r1,r2 = rots[s]
            ct ^= (((ct<<r1)|(ct>>(W-r1)))&((1<<W)-1)) & (((ct<<r2)|(ct>>(W-r2)))&((1<<W)-1))

        for i in range(W):
            gen_dimacs2.clauses.append([cur.bits[i]] if (ct>>i)&1 else [-cur.bits[i]])

        g2 = Glucose3()
        for c in gen_dimacs2.clauses: g2.add_clause(c)
        r = g2.solve()
        print(f"  Stage {stage}: {'OK' if r else 'FAIL'} (expected {ct:016x})")
        g2.delete()
