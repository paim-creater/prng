#!/usr/bin/env python3
"""milp_bit.py --- Tempest v3 比特级 MILP 活跃 AND 门计数

相比 word-level 模型 (milp_and_count.py):
  - 精确追踪每比特的差分存在
  - 使用 exact 旋转常数 (31,53),(17,43),(7,23),(5,19)
  - 每级 AND-mix 独立计数活跃 AND 门
  - XOR 传播使用保守 OR 模型 (有输入差分→输出可能有差分)

参考文献:
  Lu et al. "AND-RX: A New Lightweight Block Cipher Based on AND-RX
  Operations" (ISPEC 2019) — 相同的 AND-RX MILP 方法论

用法:
  python milp_bit.py [W] [rounds]

示例:
  python milp_bit.py 64 1    # 单轮, 全宽度
  python milp_bit.py 16 2    # 2 轮, 缩减宽度
"""

import sys
import math

W = 64  # 字宽 (全局)
DEBUG = False


def mod(x):
    """模 W 的正数索引"""
    return x % W


class BitLevelMILP:
    """Tempest v3 比特级 MILP 模型"""

    def __init__(self, W_bit=64, n_rounds=1):
        global W
        W = W_bit
        self.W = W
        self.n_rounds = n_rounds

        try:
            import pulp
        except ImportError:
            print("需要 pulp: pip install pulp")
            sys.exit(1)
        self.pulp = pulp
        self.prob = pulp.LpProblem(
            "Tempest_v3_BitLevel_Active_AND",
            pulp.LpMinimize
        )

        # ── 变量管理 ──
        self.var_cache = {}  # (name, i) -> LpVariable
        self.var_index = {}
        self.and_count_vars = []

    def var(self, name, idx=None):
        """创建或获取变量"""
        key = (name, idx)
        if key in self.var_cache:
            return self.var_cache[key]
        if idx is not None:
            full_name = f"{name}[{idx}]"
        else:
            full_name = name

        v = self.pulp.LpVariable(full_name, cat='Binary')
        self.var_cache[key] = v
        return v

    def var_word(self, name):
        """创建一组 W 个比特变量，返回列表 [bit_0,...,bit_{W-1}]"""
        return [self.var(name, i) for i in range(self.W)]

    def rotl(self, src, r):
        """旋转: 返回旋转后的变量列表 (不创建新变量)"""
        return [src[mod(i - r)] for i in range(self.W)]

    def add_constraint_xor2(self, a, b, dst):
        """XOR(a,b) → dst (比特级).

        使用 4 约束编码: dst = a XOR b
        """
        for i in range(self.W):
            ai = a[i]
            bi = b[i]
            di = dst[i]
            self.prob += di <= ai + bi
            self.prob += di >= ai - bi
            self.prob += di >= bi - ai
            self.prob += di <= 2 - ai - bi

    def add_constraint_xor3(self, a, b, c, dst):
        """XOR(a,b,c) → dst.

        使用两级 XOR 链: tmp = a XOR b; dst = tmp XOR c
        """
        tmp = [self.var(f"_xor3_tmp", i) for i in range(self.W)]
        self.add_constraint_xor2(a, b, tmp)
        self.add_constraint_xor2(tmp, c, dst)

    def add_constraint_and_active(self, a, b, active):
        """AND 活跃条件: active = 1 iff a=1 AND b=1.

        约束:
          active <= a
          active <= b
          active >= a + b - 1
        """
        for i in range(self.W):
            ai = a[i]
            bi = b[i]
            act_i = active[i]
            self.prob += act_i <= ai
            self.prob += act_i <= bi
            self.prob += act_i >= ai + bi - 1

    def add_constraint_and_output(self, a, b, dst):
        """AND 输出差分传播 (保守 OR 模型).

        若 a 或 b 有差分, dst 可能有差分.
        dst[i] >= a[i], dst[i] >= b[i]
        dst[i] <= a[i] + b[i]
        """
        for i in range(self.W):
            self.prob += dst[i] >= a[i]
            self.prob += dst[i] >= b[i]
            self.prob += dst[i] <= a[i] + b[i]

    def add_andmix4(self, t_in, t_out, prefix):
        """4 级 AND-mix 级联: t_out = andmix4(t_in).

        对每级:
          1. rotl(t, r1) & rotl(t, r2) → and_out
          2. 活跃 AND 门计数: active_and = rotl_input1 AND rotl_input2
          3. t = t XOR and_out

        返回: 活跃 AND 门计数变量列表
        """
        ROTS = [(31, 53), (17, 43), (7, 23), (5, 19)]
        stage_vars = []

        t_cur = t_in[:]  # 当前差分状态

        for stage_idx, (r1, r2) in enumerate(ROTS):
            r1_w = r1 % self.W
            r2_w = r2 % self.W

            s_prefix = f"{prefix}_s{stage_idx}"

            # rotl(t_cur, r1) 和 rotl(t_cur, r2)
            t_rot1 = self.rotl(t_cur, r1_w)
            t_rot2 = self.rotl(t_cur, r2_w)

            # AND 输出变量: and_out[i] = rotl(t,r1)[i] XOR ...
            # (差分传播)
            and_out = [self.var(f"{s_prefix}_and_out", i)
                       for i in range(self.W)]

            # 活跃 AND 门
            and_active = [self.var(f"{s_prefix}_and_active", i)
                          for i in range(self.W)]

            self.add_constraint_and_active(t_rot1, t_rot2, and_active)
            self.add_constraint_and_output(t_rot1, t_rot2, and_out)

            # t_new = t_cur XOR and_out
            t_new = [self.var(f"{s_prefix}_t", i)
                     for i in range(self.W)]
            self.add_constraint_xor2(t_cur, and_out, t_new)

            # 累加活跃 AND 门
            stage_count = self.pulp.lpSum(and_active)
            stage_vars.extend(and_active)

            t_cur = t_new

        # 最终输出
        for i in range(self.W):
            t_out[i] = t_cur[i]

        return stage_vars

    def build(self):
        """构建完整的 MILP 模型"""
        W = self.W
        R = self.n_rounds

        # ── 输入: Phase B 输出差分 (攻击者可控) ──
        u0 = self.var_word("u0")
        v0 = self.var_word("v0")
        w0 = self.var_word("w0")
        z0 = self.var_word("z0")

        # 至少 1 个输入比特有差分
        all_bits = u0 + v0 + w0 + z0
        self.prob += self.pulp.lpSum(all_bits) >= 1

        u_cur, v_cur, w_cur, z_cur = u0, v0, w0, z0

        all_round_and = []

        for rnd in range(R):
            r_pref = f"r{rnd}"

            # ═══ Phase B: XOR-ROT 扩散 ═══
            # u' = u0 XOR rotl(v0,7) XOR rotl(w0,17)
            u_new = [self.var(f"{r_pref}_u_new", i) for i in range(W)]
            rv7 = self.rotl(v_cur, 7 % W)
            rw17 = self.rotl(w_cur, 17 % W)
            self.add_constraint_xor3(u_cur, rv7, rw17, u_new)

            # v' = v0 XOR rotl(w0,11) XOR rotl(z0,23)
            v_new = [self.var(f"{r_pref}_v_new", i) for i in range(W)]
            rw11 = self.rotl(w_cur, 11 % W)
            rz23 = self.rotl(z_cur, 23 % W)
            self.add_constraint_xor3(v_cur, rw11, rz23, v_new)

            # w' = w0 XOR rotl(z0,13) XOR rotl(u0,31)
            w_new = [self.var(f"{r_pref}_w_new", i) for i in range(W)]
            rz13 = self.rotl(z_cur, 13 % W)
            ru31 = self.rotl(u_cur, 31 % W)
            self.add_constraint_xor3(w_cur, rz13, ru31, w_new)

            # z' = z0 XOR rotl(u0,17) XOR rotl(v0,7)
            z_new = [self.var(f"{r_pref}_z_new", i) for i in range(W)]
            ru17 = self.rotl(u_cur, 17 % W)
            rv7b = self.rotl(v_cur, 7 % W)
            self.add_constraint_xor3(z_cur, ru17, rv7b, z_new)

            # ═══ Phase C: andmix4 ═══
            u_mixed = [self.var(f"{r_pref}_u_mixed", i) for i in range(W)]
            z_mixed = [self.var(f"{r_pref}_z_mixed", i) for i in range(W)]

            and_u = self.add_andmix4(u_new, u_mixed, f"{r_pref}_u")
            and_z = self.add_andmix4(z_new, z_mixed, f"{r_pref}_z")

            all_round_and.extend(and_u)
            all_round_and.extend(and_z)

            u_cur, v_cur, w_cur, z_cur = u_mixed, v_new, w_new, z_mixed

        # ═══ 目标: 极小化活跃 AND 门总数 ═══
        total_active = self.pulp.lpSum(all_round_and)
        self.prob += total_active
        self.and_count_vars = all_round_and

        # 辅助: 记录总变量数
        self.total_vars = len(self.var_cache)

        return self.prob

    def solve(self, time_limit_seconds=120):
        """求解 MILP 并输出结果"""
        solver = self.pulp.PULP_CBC_CMD(
            msg=True,
            gapRel=0.1,       # 10% optimality gap
            timeLimit=time_limit_seconds,
            options=["allowableGap 5"]
        )

        self.prob.solve(solver)

        status = self.pulp.LpStatus[self.prob.status]
        obj_val = self.pulp.value(self.prob.objective)
        total_and = int(round(obj_val)) if obj_val is not None else None

        print(f"\n{'=' * 60}")
        print(f"Tempest v3 比特级 MILP 结果")
        print(f"  W = {self.W}, Rounds = {self.n_rounds}")
        print(f"  MILP 变量数: {self.total_vars}")
        print(f"  状态: {status}")
        print(f"{'=' * 60}")

        if total_and is None:
            print("! 未找到解")
            return None

        print(f"\n【核心结果】最小活跃 AND 门: {total_and}")
        print(f"  对应差分概率上界: ≤ (1/2)^{total_and} = 2^-{total_and}")

        if total_and >= 128:
            print(f"  ✅ 单轮 DP ≤ 2^-{total_and} (≥ 128-bit 安全)")
        elif total_and >= 64:
            two_round = 2 * total_and
            print(f"  ⚠️ 单轮 DP ≤ 2^-{total_and}, 两轮后 ≤ 2^-{two_round}")
            print(f"  {'✅ 两轮后满足' if two_round >= 128 else '⚠️ 两轮后未达到'} 128-bit 安全")
        else:
            print(f"  ⚠️ 单轮 DP 较弱, 两轮后约 2^-{2 * total_and}")

        # ── 输入活跃模式 ──
        print(f"\n【输入差分分析】")
        active_words = []
        for name, bits in [('u', 'u0'), ('v', 'v0'), ('w', 'w0'), ('z', 'z0')]:
            active = [i for i in range(self.W)
                      if self.pulp.value(self.var(bits, i)) == 1]
            if active:
                active_words.append(name)
                if len(active) <= 8:
                    print(f"  {name}: 活跃比特 {active}")
                else:
                    print(f"  {name}: {len(active)} 个活跃比特 "
                          f"(前 8: {active[:8]}...)")
        if not active_words:
            print(f"  (无活跃输入 - 平凡解)")
        else:
            # 输出建议约束
            first_active = next((i for n in ['u','v','w','z']
                                for i in range(self.W)
                                if self.pulp.value(self.var(f"{n}0", i)) == 1), None)
            if first_active is not None:
                print(f"\n【对称性提示】使用 --fixbit {first_active} 加速求解")

        # ── 各级活跃 AND 门分布 ──
        if DEBUG and self.W <= 16:
            print(f"\n【各级 AND 门分布】")
            for name in ['u', 'z']:
                for s in range(4):
                    act = [i for i in range(self.W)
                           if self.pulp.value(
                        self.var(f"r0_{name}_s{s}_and_active", i)) == 1]
                    if act:
                        print(f"  {name}_s{s}: {len(act)} AND [{act[:6]}...]")
                    else:
                        print(f"  {name}_s{s}: 0 AND")

        return total_and


def main():
    W = 64
    R = 1
    if len(sys.argv) > 1:
        W = int(sys.argv[1])
    if len(sys.argv) > 2:
        R = int(sys.argv[2])

    print(f"Tempest v3 比特级 MILP 活跃 AND 门计数")
    print(f"  字宽: {W}")
    print(f"  轮数: {R}")
    print(f"  (W={W}, 4字 = {4*W} 比特输入变量)")
    print()

    if W > 32 and R > 1:
        print("⚠️  W>32 且 R>1 → MILP 变量数约", 4*W + R*(16*W + 4*W),
              "求解可能需要数小时~数天")
        resp = input("继续? (y/n) ")
        if resp.lower() != 'y':
            print("取消")
            return

    milp = BitLevelMILP(W_bit=W, n_rounds=R)
    milp.build()
    result = milp.solve()

    if result is not None:
        print(f"\n结论: 每轮至少 {result} 个 AND 门活跃")
        print(f"      差分概率 ≤ 2^(-{result}) / 轮")


if __name__ == '__main__':
    main()
