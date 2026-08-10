# Tempest v3 标准自动化密码分析工具指南

本文档指导如何使用密码学领域的标准自动化工具对 Tempest v3 进行差分/线性/代数密码分析。

## 环境要求

- **操作系统:** MSYS2 MinGW-w64 (本机) / WSL Ubuntu (推荐) / Linux 原生 (最佳)
- **编译器:** GCC 或 Clang (已有)
- **Python:** 3.8+ (已有)

---

## 1. 活跃 AND 门计数 — MILP 方法

**原理:** 将 Tempest v3 的差分传播编码为混合整数线性规划 (MILP) 约束，目标是找到最小活跃 AND 门数。这是现代对称密码分析的标准方法 (Sun et al. 2014; Xiang et al. 2016)。

### 1.1 Python + pulp (本机运行)

```bash
pip install pulp
python milp_and_count.py 64
```

### 1.2 Python + OR-Tools (备用)

```bash
pip install ortools
# 修改 milp_and_count.py 底部注释的 ortools 版本
```

### 1.3 SageMath (学术标准环境)

```bash
# 方法一: conda 安装 (Windows 友好)
conda install -c conda-forge sagemath

# 方法二: WSL Ubuntu
wsl
sudo apt install sagemath

# SageMath MILP 示例:
# sage -c "
# p = MixedIntegerLinearProgram()
# a = p.new_variable(binary=True)
# p.set_objective(sum(a[i] for i in range(64)))
# p.solve()
# "
```

---

## 2. SAT-Solver 攻击

### 2.1 CaDiCaL — 安装 (MSYS2 / MinGW)

```bash
# 从 GitHub 克隆
git clone https://github.com/arminbiere/cadical.git
cd cadical
./configure
make -j4
# 生成的可执行文件: build/cadical

# 测试:
./build/cadical ../submission/code/sat_analysis/tempest_W16_R1.cnf
```

### 2.2 Kissat — 安装

```bash
git clone https://github.com/arminbiere/kissat.git
cd kissat
./configure
make -j4
# 生成: build/kissat
```

### 2.3 CryptoMiniSat — 安装

```bash
git clone https://github.com/msoos/cryptominisat.git
cd cryptominisat
mkdir build && cd build
cmake ..
make -j4
# 注意: CryptoMiniSat 支持 XOR 子句 (无需拆分为 CNF)
# 对 AND-RX 密码特别有用
```

### 2.4 生成 Tempest v3 CNF 并求解

```bash
# 1. 编译 CNF 生成器
cd submission/code/sat_analysis
gcc -O3 -o gen_tempest_cnf gen_tempest_cnf.c -I..

# 2. 生成 W=16, R=1 的 CNF (可解)
./gen_tempest_cnf 16 1 > tempest_W16_R1.cnf
# 预计: ~2000 变量, ~7000 子句

# 3. 用 CaDiCaL 求解
~/cadical/build/cadical tempest_W16_R1.cnf

# 4. 生成 W=32, R=1 (边界)
./gen_tempest_cnf 32 1 > tempest_W32_R1.cnf
# 预计: ~6000 变量, ~23000 子句

# 5. 生成 W=64, R=1 (困难)
./gen_tempest_cnf 64 1 > tempest_W64_R1.cnf
# 预计: ~10000 变量, ~38000 子句
```

### 2.5 预期结果

| W | R | 变量 | 子句 | 预期求解时间 |
|---|---|---|---|---|
| 16 | 1 | ~2,000 | ~7,000 | <10秒 |
| 32 | 1 | ~6,000 | ~23,000 | ~5-30分钟 |
| 64 | 1 | ~10,240 | ~38,160 | 数小时~数天 |
| 64 | 2 | ~20,224 | ~76,320 | 不可解 (>10^5 变量) |

**与 cmul 方案的对比:** AND-only 电路每个 AND 门仅 3 子句，而 cmul 的
32×32 乘法器编码需要 ~1024 子句。因此纯 GF(2) Tempest v3 的 CNF
编码比 4-cmul 版本紧凑约 20 倍。

---

## 3. SMT 求解器 — CryptoSMT

**CryptoSMT** 是基于 STP/Boolector 的 SMT 框架，专为对称密码的差分/线性分析设计。

### 3.1 安装 (WSL Ubuntu)

```bash
# 在 WSL 中:
sudo apt install python3-pip git
git clone https://github.com/kste/cryptosmt.git
cd cryptosmt
pip install -r requirements.txt
```

### 3.2 Tempest v3 差分分析脚本

```python
# cryptosmt_tempest.py — 在 CryptoSMT 框架中运行
from cryptosmt import SMT

# 定义 Tempest v3 单轮
# CryptoSMT 使用位向量 (BitVector) 表示状态
W = 64
smt = SMT()

# 输入变量
u = smt.bitvec('u', W)
v = smt.bitvec('v', W)
w = smt.bitvec('w', W)
z = smt.bitvec('z', W)

# 差分变量
du = smt.bitvec('du', W)
dv = smt.bitvec('dv', W)
dw = smt.bitvec('dw', W)
dz = smt.bitvec('dz', W)

# 非平凡差分约束
smt.add(smt.Or(du != 0, dv != 0, dw != 0, dz != 0))

# Phase B
u0, v0, w0, z0 = u, v, w, z
u1 = u0 ^ smt.rotl(v0, 7) ^ smt.rotl(w0, 17)
v1 = v0 ^ smt.rotl(w0, 11) ^ smt.rotl(z0, 23)
w1 = w0 ^ smt.rotl(z0, 13) ^ smt.rotl(u0, 31)
z1 = z0 ^ smt.rotl(u0, 17) ^ smt.rotl(v0, 7)

# Phase C (andmix4)
def andmix4(smt, t):
    t = t ^ (smt.rotl(t, 31) & smt.rotl(t, 53))
    t = t ^ (smt.rotl(t, 17) & smt.rotl(t, 43))
    t = t ^ (smt.rotl(t, 7) & smt.rotl(t, 23))
    t = t ^ (smt.rotl(t, 5) & smt.rotl(t, 19))
    return t

u2 = andmix4(smt, u1)
z2 = andmix4(smt, z1)

# 差分传播
du1 = u0 ^ (u0 ^ du) ^ smt.rotl(v0 ^ (v0 ^ dv), 7) ^ ...
# CryptoSMT 自动处理差分传播

# 目标: 最小化活跃 AND 门数
# 使用 SAT 求解器的优化模式
result = smt.solve()
```

---

## 4. 差分搜索 — 自动化

### 4.1 随机差分搜索 (已有 divprop.c)

```bash
cd submission/code
gcc -O3 -o divprop divprop.c -I.. -lm
./divprop
```

### 4.2 基于 MILP 的最优差分路径搜索

Python 脚本 `milp_and_count.py` 输出最少活跃 AND 门数。
对于更精确的差分路径搜索 (带具体旋转常数的比特级路径)，
需要在 MILP 模型中精确编码每个 AND 门的差分传播表。

### 4.3 可行方向

1. **单轮最优差分路径:** 使用 MILP + CBC/GLPK 求解
2. **两轮截断差分:** 使用 MILP 搜索截断差分路径
3. **差分概率估算:** 通过活跃 AND 门数估算 DP ≤ (1/2)^{active_count}

---

## 5. 积分分析 / Division Property

### 5.1 Todo-Yoshiba MILP 方法

Todo (2015) 提出的 generalized integral property 的 MILP 建模方法：

```python
# 对 Tempest v3 的 division property MILP 模型
# 每个比特一个二元变量 [x_i] 表示该比特的 division property
# AND: [x] + [y] = [z] (分量乘法)
# XOR: [x] + [y] -> [z] where z = max(x, y)

from sage.all import *
p = MixedIntegerLinearProgram()
# ... (详细建模见论文 §5.2)
```

### 5.2 简化验证

对于 Tempest v3，代数完备性 (deg ≥ 256) 直接保证了
积分区分器需要 ≥ 2^257 选择明文——等价于穷举。

---

## 6. 工作流建议

### 快速验证 (1 天)

```bash
# 1. MILP 活跃 AND 门计数 (本机)
pip install pulp
python milp_and_count.py 64

# 2. 缩减宽度 SAT (本机)
gcc -o gen_cnf gen_tempest_cnf.c
./gen_cnf 16 1 > test.cnf
# → 使用自带 DPLL 求解器验证

# 3. 差分概率扫描 (已有)
gcc -o cryptanalysis_v2 cryptanalysis_v2.c
./cryptanalysis_v2
```

### 完整密码分析 (1-2 周, 需要 WSL/Linux)

```bash
# 1. 安装 CaDiCaL + MILP 求解器
# 2. W=32 全轮 SAT 求解
# 3. MILP 最优差分路径
# 4. Division property MILP
# 5. 线性相关性分析
```

### 论文级分析 (1-3 月, 专业环境)

```bash
# 1. CryptoSMT 全轮差分搜索
# 2. MILP 最优差分/线性轨迹
# 3. CP (Constraint Programming) 建模
# 4. 自动化密钥恢复攻击验证
# 5. 跨平台第三方密码分析
```

---

## 参考文献

1. Sun et al. "Automatic Security Evaluation of Block Ciphers with MILP"
   (ASIACRYPT 2014)
2. Xiang et al. "Applying MILP Method to Searching Integral Distinguishers"
   (CRYPTO 2016)
3. Todo "Structural Evaluation by Generalized Integral Property"
   (EUROCRYPT 2015)
4. Mouha et al. "Differential and Linear Cryptanalysis Using Mixed-Integer
   Linear Programming" (Inscrypt 2011)
5. Lu et al. "AND-RX: A New Lightweight Block Cipher Based on AND-RX
   Operations" (ISPEC 2019) — 最接近 Tempest v3 的设计
6. CaDiCaL: https://github.com/arminbiere/cadical
7. CryptoMiniSat: https://github.com/msoos/cryptominisat
8. CryptoSMT: https://github.com/kste/cryptosmt
