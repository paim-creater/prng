/* diff_trace.c --- Tempest v3 差分传播追踪器
 *
 * 对每个单比特输入差分位置，追踪其通过 Phase B + andmix4×4
 * 的传播路径，统计活跃 AND 门数量。
 *
 * AND 输出模型: 保守 OR（任一输入有差分 → 输出可能有差分）
 * 这忽略了 XOR 取消，给出的是上界（最差情况扩散）。
 *
 * 编译:
 *   gcc -O3 -o diff_trace diff_trace.c
 *   ./diff_trace
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>

#define W 64

/* ─── 差分追踪 ─── */
typedef struct {
    uint64_t bits[4];  /* u, v, w, z */
} DiffState;

static inline int get_bit(const DiffState *s, int word, int bit) {
    return (s->bits[word] >> (bit % W)) & 1;
}
static inline void set_bit(DiffState *s, int word, int bit) {
    s->bits[word] |= (1ULL << (bit % W));
}

static int popcount64(uint64_t x) {
    return __builtin_popcountll(x);
}

/* ─── Phase B: XOR-ROT 扩散 (OR 模型) ─── */
static void phase_b_or(const DiffState *in, DiffState *out) {
    memset(out, 0, sizeof(*out));
    /* u' = u0 XOR rotl(v0,7) XOR rotl(w0,17) */
    for (int i = 0; i < W; i++) {
        if (get_bit(in, 0, i) || get_bit(in, 1, (i - 7) % W) || get_bit(in, 2, (i - 17) % W))
            set_bit(out, 0, i);
    }
    /* v' = v0 XOR rotl(w0,11) XOR rotl(z0,23) */
    for (int i = 0; i < W; i++) {
        if (get_bit(in, 1, i) || get_bit(in, 2, (i - 11) % W) || get_bit(in, 3, (i - 23) % W))
            set_bit(out, 1, i);
    }
    /* w' = w0 XOR rotl(z0,13) XOR rotl(u0,31) */
    for (int i = 0; i < W; i++) {
        if (get_bit(in, 2, i) || get_bit(in, 3, (i - 13) % W) || get_bit(in, 0, (i - 31) % W))
            set_bit(out, 2, i);
    }
    /* z' = z0 XOR rotl(u0,17) XOR rotl(v0,7) */
    for (int i = 0; i < W; i++) {
        if (get_bit(in, 3, i) || get_bit(in, 0, (i - 17) % W) || get_bit(in, 1, (i - 7) % W))
            set_bit(out, 3, i);
    }
}

/* ─── AND-mix 单级 (OR 传播) ───
 *   输入: t (64-bit diff pattern)
 *   输出: after t ^= rotl(t,r1) & rotl(t,r2)
 *   返回: 该级活跃 AND 门数
 */
static int andmix_stage_or(uint64_t *t, int r1, int r2) {
    uint64_t rot1 = ((*t) << r1) | ((*t) >> (W - r1));
    uint64_t rot2 = ((*t) << r2) | ((*t) >> (W - r2));

    /* 活跃 AND 门: rot1[i] == 1 AND rot2[i] == 1 */
    uint64_t active = rot1 & rot2;
    int count = popcount64(active);

    /* AND 输出差分 (OR 模型) */
    uint64_t and_out = rot1 | rot2;

    /* t_new = t XOR and_out */
    *t ^= and_out;

    return count;
}

/* ─── andmix4 完整 4 级 ─── */
static int andmix4_or(uint64_t t) {
    int total = 0;
    int rots[4][2] = {{31,53},{17,43},{7,23},{5,19}};
    for (int s = 0; s < 4; s++) {
        int c = andmix_stage_or(&t, rots[s][0], rots[s][1]);
        total += c;
        printf("    级%d: +%d AND (hw=%d)\n", s, c, popcount64(t));
    }
    return total;
}

/* ─── 1-bit 输入差分完整追踪 ─── */
static int trace_1bit(void) {
    int best_and = 999, worst_and = 0, total_and = 0;
    int best_bit = -1, worst_bit = -1;

    for (int bit = 0; bit < W; bit++) {
        DiffState in, after_b;
        memset(&in, 0, sizeof(in));
        set_bit(&in, 0, bit);  /* u 的第 bit 位 */

        phase_b_or(&in, &after_b);

        /* andmix4 on u */
        printf("bit %2d: PhaseB -> u_hw=%d v_hw=%d w_hw=%d z_hw=%d ",
               bit, popcount64(after_b.bits[0]), popcount64(after_b.bits[1]),
               popcount64(after_b.bits[2]), popcount64(after_b.bits[3]));

        int and_u = (after_b.bits[0] != 0) ? andmix4_or(after_b.bits[0]) : 0;
        int and_z = (after_b.bits[3] != 0) ? andmix4_or(after_b.bits[3]) : 0;
        int total = and_u + and_z;
        printf("  total: %d\n", total);

        total_and += total;
        if (total < best_and) { best_and = total; best_bit = bit; }
        if (total > worst_and) { worst_and = total; worst_bit = bit; }
    }

    printf("\n===== W=64 单比特输入统计 =====\n");
    printf("最佳输入: bit %d → %d AND\n", best_bit, best_and);
    printf("最差输入: bit %d → %d AND\n", worst_bit, worst_and);
    printf("平均活跃 AND: %.1f\n", (double)total_and / W);
    return best_and;
}

int main(void) {
    printf("Tempest v3 差分传播追踪 (OR 传播模型)\n");
    printf("W = %d, 1-bit 输入差分\n\n", W);

    int min_and = trace_1bit();
    printf("\n结论: 1-bit 输入下最少活跃 AND = %d\n", min_and);
    printf("      单轮 DP 上界 (保守) ≤ 2^(-%d)\n", min_and);
    printf("      两轮 + 输出 DP ≤ 2^(-%d)\n", min_and * 2 + 4);
    return 0;
}
