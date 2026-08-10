#!/usr/bin/env python3
"""diff_trace.py --- Tempest v3 OR-差分传播追踪

对每个单比特输入差分位置，追踪其通过 Phase B + andmix4×4
的传播路径，统计活跃 AND 门数量。

AND 输出模型: 保守 OR（任一输入有差分 → 输出可能有差分）
这忽略了 XOR 取消，给出的是上界（最差情况扩散）。

运行: python diff_trace.py
"""

W = 64


def popcount(x):
    return x.bit_count()


def rotl(x, r):
    return ((x << r) | (x >> (W - r))) & ((1 << W) - 1)


def phase_b_or(diff):
    """Phase B: XOR-ROT 扩散 (OR 模型)"""
    u, v, w, z = diff
    u_out = 0
    v_out = 0
    w_out = 0
    z_out = 0
    for i in range(W):
        s1 = (u >> i) & 1
        s2 = (v >> ((i - 7) % W)) & 1
        s3 = (w >> ((i - 17) % W)) & 1
        if s1 or s2 or s3:
            u_out |= (1 << i)

        s1 = (v >> i) & 1
        s2 = (w >> ((i - 11) % W)) & 1
        s3 = (z >> ((i - 23) % W)) & 1
        if s1 or s2 or s3:
            v_out |= (1 << i)

        s1 = (w >> i) & 1
        s2 = (z >> ((i - 13) % W)) & 1
        s3 = (u >> ((i - 31) % W)) & 1
        if s1 or s2 or s3:
            w_out |= (1 << i)

        s1 = (z >> i) & 1
        s2 = (u >> ((i - 17) % W)) & 1
        s3 = (v >> ((i - 7) % W)) & 1
        if s1 or s2 or s3:
            z_out |= (1 << i)

    return (u_out, v_out, w_out, z_out)


def andmix_stage_or(t, r1, r2):
    """AND-mix 单级 (OR 传播)"""
    rot1 = rotl(t, r1)
    rot2 = rotl(t, r2)

    # 活跃 AND: rot1[i] == 1 AND rot2[i] == 1
    active = rot1 & rot2
    count = popcount(active)

    # AND 输出差分 (OR 模型)
    and_out = rot1 | rot2

    # t_new = t XOR and_out
    t_new = t ^ and_out

    return t_new, count


def andmix4_or(t):
    """andmix4 完整 4 级"""
    ROTS = [(31, 53), (17, 43), (7, 23), (5, 19)]
    total = 0
    for s, (r1, r2) in enumerate(ROTS):
        t, c = andmix_stage_or(t, r1, r2)
        total += c
    return t, total


def trace_all_1bit():
    """对所有 64 个单比特位置追踪差分传播"""
    results = []

    for bit in range(W):
        # 输入: u 的单比特差分
        in_diff = (1 << bit, 0, 0, 0)

        # Phase B
        after_b = phase_b_or(in_diff)
        hw_u = popcount(after_b[0])
        hw_v = popcount(after_b[1])
        hw_w = popcount(after_b[2])
        hw_z = popcount(after_b[3])

        # andmix4
        _, and_u = andmix4_or(after_b[0]) if after_b[0] else (0, 0)
        _, and_z = andmix4_or(after_b[3]) if after_b[3] else (0, 0)
        total_and = and_u + and_z

        results.append((bit, hw_u, hw_v, hw_w, hw_z, total_and))
        print(f"bit {bit:2d}: PhaseB-> u={hw_u:2d} v={hw_v:2d} w={hw_w:2d} "
              f"z={hw_z:2d} | and u={and_u:3d} z={and_z:2d} total={total_and:3d}")

    return results


def main():
    print(f"Tempest v3 OR-差分传播追踪 (W={W})")
    print(f"{'=' * 70}")

    results = trace_all_1bit()

    totals = [r[5] for r in results]
    min_and = min(totals)
    max_and = max(totals)
    avg_and = sum(totals) / len(totals)

    min_bits = [r[0] for r in results if r[5] == min_and]
    max_bits = [r[0] for r in results if r[5] == max_and]

    print(f"\n{'=' * 70}")
    print(f"W={W} 单比特输入统计 (OR 模型)")
    print(f"{'=' * 70}")
    print(f"最少活跃 AND: {min_and} (bit {min_bits})")
    print(f"最多活跃 AND: {max_and} (bit {max_bits})")
    print(f"平均活跃 AND: {avg_and:.1f}")
    print(f"\n安全性估计 (OR 模型上界):")
    print(f"  单轮 DP ≤ 2^(-{min_and})  (最少活跃 AND)")
    print(f"  平均 DP ≈ 2^(-{avg_and:.0f})")
    print(f"  两轮 + 输出 DP ≤ 2^(-{min_and * 2 + 4})")

    # W=12 验证 (对比 MILP)
    def run_W(width):
        global W
        old = W
        W = width
        r = trace_all_1bit()
        W = old
        return min(rr[5] for rr in r)

    print(f"\n{'=' * 70}")
    print("缩减宽度对比验证 (OR 模型 vs MILP 最优)")
    min_12 = run_W(12)
    min_8 = run_W(8)
    print(f"  W=12 OR={min_12}, MILP最优=4  (OR模型高估扩散, 合理)")
    print(f"  W=8  OR={min_8},  MILP最优=8  (OR模型低估扩散! 需分析)")


if __name__ == '__main__':
    main()
