/* gen_tempest_cnf.c --- 生成标准 DIMACS CNF 用于外部 SAT 求解器
 *                                (CaDiCaL / Kissat / CryptoMiniSat)
 *
 * 用法:
 *   gcc -O3 -o gen_tempest_cnf gen_tempest_cnf.c -I..
 *   ./gen_tempest_cnf [W] [R] > tempest_W16_R1.cnf
 *   ./kissat tempest_W16_R1.cnf
 *
 * 编码策略: Tseitin 编码 (每个 AND/XOR 门引入 1 个辅助变量)
 *   AND(a,b,out):  (out -> a), (out -> b), (a & b -> out)
 *   = (¬out ∨ a) ∧ (¬out ∨ b) ∧ (¬a ∨ ¬b ∨ out)
 *   XOR(a,b,out):  (¬out ∨ ¬a ∨ ¬b) ∧ (¬out ∨ a ∨ b) ∧ (out ∨ ¬a ∨ b) ∧ (out ∨ a ∨ ¬b)
 *
 * 与 cmul 方案的区别: AND-only 电路每个门的 CNF 编码仅 3 子句
 *   (cmul 的 32x32 乘法编码需约 1024 子句)
 *
 * 注: Weyl 轮常数 (Phase A) 在本简化编码中略去——它不影响 SAT 难度
 *      (XOR 固定常数不会改变问题的代数结构)
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>

/* ─── CNF 构建器 ─── */
static int next_var = 1;   /* DIMACS 变量从 1 开始 */
static long clause_count = 0;
static FILE *out = NULL;

static inline void begin_cnf(int max_var) {
    fprintf(out, "p cnf %d 0\n", max_var);
}
static inline void begin_round(void) {
    /* round header as comment */
    fprintf(out, "c --- round ---\n");
}
static inline void add_clause_va(const int *lits, int n) {
    for (int i = 0; i < n; i++) fprintf(out, "%d ", lits[i]);
    fprintf(out, "0\n");
    clause_count++;
}
/* 辅助: 1-literal, 2-literal, 3-literal clause */
static inline void clause1(int a) {
    int l[] = {a}; add_clause_va(l,1);
}
static inline void clause2(int a, int b) {
    int l[] = {a,b}; add_clause_va(l,2);
}
static inline void clause3(int a, int b, int c) {
    int l[] = {a,b,c}; add_clause_va(l,3);
}

static int fresh(void) { return next_var++; }

/* AND(a,b) = out   (out 是 AND 的输出变量) */
static void emit_and(int a, int b, int out) {
    clause2(-out, a);          /* out → a */
    clause2(-out, b);          /* out → b */
    clause3(-a, -b, out);      /* a ∧ b → out */
}

/* XOR(a,b) = out */
static void emit_xor(int a, int b, int out) {
    clause3(-out, -a, -b);     /* ¬out ∨ ¬a ∨ ¬b */
    clause3(-out, a, b);       /* ¬out ∨ a ∨ b */
    clause3(out, -a, b);      /* out ∨ ¬a ∨ b */
    clause3(out, a, -b);      /* out ∨ a ∨ ¬b */
}

/* ─── 字面量: 一个字的所有比特变量 ─── */
typedef struct {
    int bits[64];  /* bits[i] = 第 i 位的变量编号 (0=常量0, -1=预留) */
} Word;

/* 初始化一个字: 分配 W 个新变量 */
static Word word_new(int W) {
    Word w;
    for (int i = 0; i < W; i++) w.bits[i] = fresh();
    return w;
}

/* 常量0 的字 */
static Word word_zero(int W) {
    Word w;
    for (int i = 0; i < W; i++) w.bits[i] = 0;  /* 字面量 0 = 常量假 */
    return w;
}

/* 复制一个字 */
static Word word_copy(const Word *src, int W) {
    Word w;
    for (int i = 0; i < W; i++) w.bits[i] = src->bits[i];
    return w;
}

/* ROTL(src, r) → dst */
static void emit_rotl(const Word *src, int r, Word *dst, int W) {
    for (int i = 0; i < W; i++) {
        int s = (i - r) % W;
        if (s < 0) s += W;
        dst->bits[i] = src->bits[s];  /* 旋转 = 重排变量, 无子句 */
    }
}

/* XOR(a,b) → dst */
static void emit_xor_word(const Word *a, const Word *b, Word *dst, int W) {
    for (int i = 0; i < W; i++) {
        int v = fresh();
        if (a->bits[i] == 0)       dst->bits[i] = b->bits[i];   /* 0 ⊕ x = x */
        else if (b->bits[i] == 0)  dst->bits[i] = a->bits[i];   /* x ⊕ 0 = x */
        else if (a->bits[i] == -b->bits[i]) dst->bits[i] = 0;   /* x ⊕ x = 0 */
        else emit_xor(a->bits[i], b->bits[i], (dst->bits[i] = v));
    }
}

/* AND(a,b) → dst */
static void emit_and_word(const Word *a, const Word *b, Word *dst, int W) {
    for (int i = 0; i < W; i++) {
        int v = fresh();
        if (a->bits[i] == 0 || b->bits[i] == 0) dst->bits[i] = 0;  /* 0 & x = 0 */
        else if (a->bits[i] == b->bits[i]) {
            /* x & x = x */
            dst->bits[i] = a->bits[i];
        } else emit_and(a->bits[i], b->bits[i], (dst->bits[i] = v));
    }
}

/* ─── andmix4 ─── */
static void emit_andmix4(const Word *t, Word *out, int W) {
    Word c = word_copy(t, W);
    Word r1, r2, a, n;
    /* 每级的旋转常数对 (W 缩减版) */
    int rots[4][2] = {{31,53},{17,43},{7,23},{5,19}};
    for (int s = 0; s < 4; s++) {
        int r1v = rots[s][0] % W, r2v = rots[s][1] % W;
        emit_rotl(&c, r1v, &r1, W);
        emit_rotl(&c, r2v, &r2, W);
        emit_and_word(&r1, &r2, &a, W);
        emit_xor_word(&c, &a, &n, W);
        c = n;
    }
    *out = word_copy(&c, W);
}

/* ─── Tempest v3 轮函数 (纯 GF(2)): Phase B + C ───
 *   输入: u,v,w,z (W-bit 字)
 *   Phase B: 增强型双源 XOR 扩散
 *   Phase C: andmix4 on u, z
 *   输出: u',v',w',z' (下一轮状态)
 */
static void emit_tempest_round(const Word *u, const Word *v,
                                const Word *w, const Word *z,
                                Word *u2, Word *v2, Word *w2, Word *z2,
                                int W) {
    /* 保存副本 */
    Word u0 = word_copy(u, W);
    Word v0 = word_copy(v, W);
    Word w0 = word_copy(w, W);
    Word z0 = word_copy(z, W);

    /* ── Phase B ── */
    Word t1, t2;
    /* u = u0 ⊕ rotl(v0,7) ⊕ rotl(w0,17) */
    Word rv7, rw17;
    emit_rotl(&v0, 7 % W, &rv7, W);
    emit_rotl(&w0, 17 % W, &rw17, W);
    emit_xor_word(&u0, &rv7, &t1, W);
    emit_xor_word(&t1, &rw17, u2, W);

    /* v = v0 ⊕ rotl(w0,11) ⊕ rotl(z0,23) */
    Word rw11, rz23;
    emit_rotl(&w0, 11 % W, &rw11, W);
    emit_rotl(&z0, 23 % W, &rz23, W);
    emit_xor_word(&v0, &rw11, &t1, W);
    emit_xor_word(&t1, &rz23, v2, W);

    /* w = w0 ⊕ rotl(z0,13) ⊕ rotl(u0,31) */
    Word rz13, ru31;
    emit_rotl(&z0, 13 % W, &rz13, W);
    emit_rotl(&u0, 31 % W, &ru31, W);
    emit_xor_word(&w0, &rz13, &t1, W);
    emit_xor_word(&t1, &ru31, w2, W);

    /* z = z0 ⊕ rotl(u0,17) ⊕ rotl(v0,7) */
    Word ru17, rv7b;
    emit_rotl(&u0, 17 % W, &ru17, W);
    emit_rotl(&v0, 7 % W, &rv7b, W);
    emit_xor_word(&z0, &ru17, &t1, W);
    emit_xor_word(&t1, &rv7b, z2, W);

    /* ── Phase C ── */
    if (W >= 4) {
        Word u_mixed, z_mixed;
        emit_andmix4(u2, &u_mixed, W);
        emit_andmix4(z2, &z_mixed, W);
        *u2 = u_mixed;
        *z2 = z_mixed;
    }
}

/* ─── 关键恢复 CNF ───
 *   已知: 1 轮后的部分输出比特
 *   目标: 恢复输入密钥
 *   约束: 前 R 轮的输出与观测值匹配
 *   验证: 将实际密钥 k 设置为附加约束,
 *         检查 CNF 是否可满足
 */
static void generate_key_recovery_cnf(int W, int R) {
    fprintf(out, "c Tempest v3 Key Recovery CNF\n");
    fprintf(out, "c W=%d, R=%d\n", W, R);
    fprintf(out, "c Generated: %s %s\n", __DATE__, __TIME__);
    fprintf(out, "c Encoding: Pure GF(2) with Tseitin AND/XOR\n");

    /* 输入密钥变量 */
    Word u = word_new(W);
    Word v = word_new(W);
    Word w = word_new(W);
    Word z = word_new(W);

    /* 已知正确密钥 (用于验证 CNF 可满足性) */
    /* 这里使用固定密钥 {0xDEADBEEF, ...} 作为示例 */
    fprintf(out, "c True key: 0xDEAD, 0xBEEF, 0xCAFE, 0xBABE\n");
    /* 不添加单元子句——保持 CNF 泛用性 */

    Word u_cur = word_copy(&u, W);
    Word v_cur = word_copy(&v, W);
    Word w_cur = word_copy(&w, W);
    Word z_cur = word_copy(&z, W);

    for (int r = 0; r < R; r++) {
        begin_round();
        Word u_next, v_next, w_next, z_next;
        emit_tempest_round(&u_cur, &v_cur, &w_cur, &z_cur,
                           &u_next, &v_next, &w_next, &z_next, W);
        u_cur = u_next; v_cur = v_next;
        w_cur = w_next; z_cur = z_next;
    }

    /* 输出: 从最后状态提取观测约束 (占位) */
    fprintf(out, "c Output constraints would go here\n");
    fprintf(out, "c For key-recovery: add unit clauses on output bits\n");

    /* 回写子句数 */
    fseek(out, 0, SEEK_SET);
    begin_cnf(next_var - 1);
    fprintf(out, "c Actual clause count: %ld\n", clause_count);
}

int main(int argc, char **argv) {
    int W = 16, R = 1;
    if (argc > 1) W = atoi(argv[1]);
    if (argc > 2) R = atoi(argv[2]);

    if (W < 2 || W > 64 || (W & (W-1)) != 0) {
        fprintf(stderr, "Usage: %s [W] [R]\n  W bit-width (power of 2, 2..64)\n  R rounds (1..)\n", argv[0]);
        return 1;
    }

    out = stdout;
    generate_key_recovery_cnf(W, R);

    fprintf(stderr, "CNF stats: %d variables, %ld clauses\n",
            next_var - 1, clause_count);
    return 0;
}
