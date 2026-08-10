#!/usr/bin/env python3
"""milp_and_count.py --- Tempest v3 活跃 AND 门计数的 MILP 模型

使用 pulp 库 (pip install pulp) 或 ortools (pip install ortools).

该模型将 Tempest v3 单轮的差分传播编码为 MILP 约束,
目标是最小化活跃 AND 门数量。

原理:
  - XOR 扩散: 若任意一个操作数有差分, 则输出可能有差分
  - AND 门:   仅当两个操作数都有差分时, AND 门为"活跃"
  - 分支数 = 从最少字传播出发, 能激活的 AND 门数量下限

用法:
  python milp_and_count.py [W]

输出:
  - 最小活跃 AND 门数
  - 对应的差分传播路径
"""

import sys

def build_milp(W=64):
    """构建 Tempest v3 单轮 MILP 模型"""

    try:
        import pulp
    except ImportError:
        print("需要安装 pulp: pip install pulp")
        print("或用 ortools 版本 (见下文)")
        sys.exit(1)

    prob = pulp.LpProblem("Tempest_v3_Active_AND_Count",
                          pulp.LpMinimize)

    # ── 变量 ──
    # a[word][bit] = 1 表示该 bit 有非零差分
    a = {}
    for w in ['u', 'v', 'w', 'z']:
        for i in range(W):
            a[(w, i)] = pulp.LpVariable(f"a_{w}{i}", cat='Binary')

    # a0 = 预扩散前的输入差分
    a0 = {}
    for w in ['u', 'v', 'w', 'z']:
        for i in range(W):
            a0[(w, i)] = pulp.LpVariable(f"a0_{w}{i}", cat='Binary')

    # 输入差分非零约束: 至少 1 个比特非零 (非平凡差分)
    prob += pulp.lpSum([a0[('u', i)] for i in range(W)] +
                       [a0[('v', i)] for i in range(W)] +
                       [a0[('w', i)] for i in range(W)] +
                       [a0[('z', i)] for i in range(W)]) >= 1

    # ── Phase B: XOR-ROT 扩散 ──
    # u' = u0 ⊕ rotl(v0,7) ⊕ rotl(w0,17)
    # 若 u0 或 rotl(v0,7) 或 rotl(w0,17) 有差分 -> u 可能有差分
    # (保守约束: 三个源中有任意一个有, 则 u 可以有)
    for i in range(W):
        u_src = a0[('u', i)]
        v_src = a0[('v', (i - 7) % W)]
        w_src = a0[('w', (i - 17) % W)]
        # a[u][i] >= u_src, a[u][i] >= v_src, a[u][i] >= w_src
        # 但更宽松: a[u][i] >= (u_src + v_src + w_src) / 3
        prob += a[('u', i)] >= u_src
        prob += a[('u', i)] >= v_src
        prob += a[('u', i)] >= w_src

    # v' = v0 ⊕ rotl(w0,11) ⊕ rotl(z0,23)
    for i in range(W):
        v_src = a0[('v', i)]
        w_src = a0[('w', (i - 11) % W)]
        z_src = a0[('z', (i - 23) % W)]
        prob += a[('v', i)] >= v_src
        prob += a[('v', i)] >= w_src
        prob += a[('v', i)] >= z_src

    # w' = w0 ⊕ rotl(z0,13) ⊕ rotl(u0,31)
    for i in range(W):
        w_src = a0[('w', i)]
        z_src = a0[('z', (i - 13) % W)]
        u_src = a0[('u', (i - 31) % W)]
        prob += a[('w', i)] >= w_src
        prob += a[('w', i)] >= z_src
        prob += a[('w', i)] >= u_src

    # z' = z0 ⊕ rotl(u0,17) ⊕ rotl(v0,7)
    for i in range(W):
        z_src = a0[('z', i)]
        u_src = a0[('u', (i - 17) % W)]
        v_src = a0[('v', (i - 7) % W)]
        prob += a[('z', i)] >= z_src
        prob += a[('z', i)] >= u_src
        prob += a[('z', i)] >= v_src

    # ── AND 门活跃计数 ──
    # andmix4 共 4 级, 每级 64 个 AND 门 (每比特 1 个)
    # 第 j 级的 AND 门活跃条件: rotl(t, r1)_i 和 rotl(t, r2)_i 都有差分
    # 保守近似: 若字的汉明重量 > 0, 该级至少 1 个 AND 门活跃

    # 每个字是否有差分 (字级变量)
    a_word = {}
    for w in ['u', 'v', 'w', 'z']:
        a_word[w] = pulp.LpVariable(f"aw_{w}", cat='Binary')
        # a_word[w] >= a[(w,i)] 对所有 i
        for i in range(W):
            prob += a_word[w] >= a[(w, i)]
        # a_word[w] <= sum_i a[(w,i)]
        prob += a_word[w] * W <= pulp.lpSum([a[(w, i)] for i in range(W)]) + W - 1

    # andmix4 施加于 u 和 z
    # 每路 4 级, 每级当输入字有差分时产生至少 1 个活跃 AND 门
    and_active_count = pulp.LpVariable("and_active", lowBound=0, cat='Integer')
    prob += and_active_count >= 4 * (a_word['u'] + a_word['z'])

    # ── 目标: 极小化活跃 AND 门数 ──
    prob += and_active_count

    # ── 求解 ──
    prob.solve(pulp.PULP_CBC_CMD(msg=True))

    status = pulp.LpStatus[prob.status]
    and_count = pulp.value(and_active_count)

    print(f"\nW={W} MILP 结果:")
    print(f"  状态: {status}")
    print(f"  最小活跃 AND 门: {and_count}")

    if status == 'Optimal' and and_count is not None:
        # 输出活跃字
        active_words = [w for w in ['u','v','w','z']
                       if pulp.value(a_word[w]) == 1]
        print(f"  活跃字: {active_words}")

        # 输出哪些输入比特有差分 (稀疏表示)
        for w in ['u','v','w','z']:
            active_bits = [i for i in range(W)
                          if pulp.value(a0[(w, i)]) == 1]
            if active_bits:
                print(f"  输入 {w} 活跃比特: {active_bits[:10]}... (共 {len(active_bits)})")

    return pulp.value(and_active_count)

def main():
    W = 64
    if len(sys.argv) > 1:
        W = int(sys.argv[1])

    print(f"Tempest v3 活跃 AND 门计数 MILP 模型")
    print(f"字宽 W={W}")
    print("=" * 50)

    count = build_milp(W)
    if count is not None:
        print(f"\n结论: 每轮至少 {count} 个 AND 门活跃")
        print(f"      对应 DP 上界 <= (1/2)^{count} = 2^{-count}")
    else:
        print("\n求解失败 (模型可能过于复杂)")

if __name__ == '__main__':
    main()

"""────────── ortools 版本 (备用) ──────────
如需使用 Google OR-Tools 而非 pulp:

from ortools.linear_solver import pywraplp
solver = pywraplp.Solver.CreateSolver('CBC')
...

优点: 直接 pip install ortools, 不需要额外 solver
缺点: API 较 pulp 复杂
"""
