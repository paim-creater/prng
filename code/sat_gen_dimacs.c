/* sat_gen_dimacs.c — Generate DIMACS CNF for reduced-round Tempest SAT attack.
 * Encodes: given known output, find the secret key.
 * W ∈ {4,8,12,16}, R ∈ {1,2}. Outputs DIMACS format to stdout. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int nv=0, nc=0;

static int newv(void) { return ++nv; }
static void cla3(FILE *f, int a, int b, int c) { fprintf(f,"%d %d %d 0\n",a,b,c); nc++; }
static void cla2(FILE *f, int a, int b) { fprintf(f,"%d %d 0\n",a,b); nc++; }
static void cla1(FILE *f, int a) { fprintf(f,"%d 0\n",a); nc++; }

/* XOR: r = a ^ b */
static int xor_gate(FILE *f, int a, int b) {
    int r = newv();
    cla3(f, -a, -b, -r); cla3(f, -a, b, r); cla3(f, a, -b, r); cla3(f, a, b, -r);
    return r;
}

/* AND: r = a & b */
static int and_gate(FILE *f, int a, int b) {
    int r = newv();
    cla3(f, -a, -b, r); cla2(f, -r, a); cla2(f, -r, b);
    return r;
}

/* Half adder: {s,co} = a + b (no carry in) */
static void half_adder(FILE *f, int a, int b, int *s, int *co) {
    *s = xor_gate(f, a, b);
    *co = and_gate(f, a, b);
}

/* Full adder: {s,co} = a + b + cin */
static void full_adder(FILE *f, int a, int b, int cin, int *s, int *co) {
    int axb = xor_gate(f, a, b);
    *s = xor_gate(f, axb, cin);
    int ab = and_gate(f, a, b);
    int ac = and_gate(f, a, cin);
    int bc = and_gate(f, b, cin);
    *co = newv();
    cla3(f, -ab, -ac, -bc);
    cla3(f, -ab, -ac, *co); cla3(f, ab, -ac, -bc);
    cla2(f, -ab, *co); cla2(f, -ac, *co); cla2(f, -bc, *co);
}

/* N-bit ADD: sum = a + b */
static void add_n(FILE *f, int *a, int *b, int *sum, int W) {
    for (int i = 0; i < W; i++) {
        int s, co;
        if (i == 0) {
            half_adder(f, a[i], b[i], &s, &co);
        } else {
            full_adder(f, a[i], b[i], co, &s, &co);
        }
        sum[i] = s;
    }
}

/* ROTL: wire renaming */
static void rotl_wire(int *in, int *out, int r, int W) {
    for (int i = 0; i < W; i++) out[i] = in[(i - r + W) % W];
}

/* cmul_hl: prod = (a_hi × b_lo) mod 2^W */
static void cmul_hl(FILE *f, int *a, int *b, int *prod, int W) {
    int HW = W/2;
    int *ahi = a + HW, *blo = b;
    /* partial products */
    int **pp = malloc(HW * sizeof(int*));
    for (int i = 0; i < HW; i++) {
        pp[i] = malloc(HW * sizeof(int));
        for (int j = 0; j < HW; j++) pp[i][j] = and_gate(f, ahi[i], blo[j]);
    }
    /* XOR-tree per output bit */
    for (int k = 0; k < W; k++) {
        int acc = -1;
        for (int i = 0; i < HW && i <= k; i++) {
            int j = k - i;
            if (j >= 0 && j < HW) {
                if (acc < 0) acc = pp[i][j];
                else acc = xor_gate(f, acc, pp[i][j]);
            }
        }
        if (acc < 0) { prod[k] = newv(); cla1(f, -prod[k]); }
        else prod[k] = acc;
    }
    for (int i = 0; i < HW; i++) free(pp[i]);
    free(pp);
}

static void cmul_lh(FILE *f, int *a, int *b, int *prod, int W) {
    int HW = W/2;
    int *alo = a, *bhi = b + HW;
    int **pp = malloc(HW * sizeof(int*));
    for (int i = 0; i < HW; i++) {
        pp[i] = malloc(HW * sizeof(int));
        for (int j = 0; j < HW; j++) pp[i][j] = and_gate(f, alo[i], bhi[j]);
    }
    for (int k = 0; k < W; k++) {
        int acc = -1;
        for (int i = 0; i < HW && i <= k; i++) {
            int j = k - i;
            if (j >= 0 && j < HW) {
                if (acc < 0) acc = pp[i][j];
                else acc = xor_gate(f, acc, pp[i][j]);
            }
        }
        if (acc < 0) { prod[k] = newv(); cla1(f, -prod[k]); }
        else prod[k] = acc;
    }
    for (int i = 0; i < HW; i++) free(pp[i]);
    free(pp);
}

int main(int argc, char **argv) {
    int W = 8, R = 1;
    if (argc > 1) W = atoi(argv[1]);
    if (argc > 2) R = atoi(argv[2]);
    if (W < 4 || W > 16) { fprintf(stderr, "W must be 4..16 (DIMACS gets huge beyond)\n"); return 1; }

    /* Create temp file for clauses, then prepend header */
    FILE *f = fopen("_temp_cnf.cnf", "w");
    if (!f) return 1;

    /* Key variables: 4 × W bits */
    int *u = malloc(W*sizeof(int)), *v = malloc(W*sizeof(int));
    int *w = malloc(W*sizeof(int)), *z = malloc(W*sizeof(int));
    for (int i = 0; i < W; i++) { u[i]=newv(); v[i]=newv(); w[i]=newv(); z[i]=newv(); }

    /* Rounds */
    for (int rnd = 0; rnd < R; rnd++) {
        /* ADD pre-diffusion */
        int *u0 = malloc(W*sizeof(int)); memcpy(u0, u, W*sizeof(int));
        int *rv=malloc(W*sizeof(int)),*rw=malloc(W*sizeof(int));
        int *rz=malloc(W*sizeof(int)),*ru0=malloc(W*sizeof(int));
        rotl_wire(v,rv,7%W,W); rotl_wire(w,rw,11%W,W);
        rotl_wire(z,rz,13%W,W); rotl_wire(u0,ru0,17%W,W);
        add_n(f, u, rv, u, W); add_n(f, v, rw, v, W);
        add_n(f, w, rz, w, W); add_n(f, z, ru0, z, W);
        free(u0); free(rv); free(rw); free(rz); free(ru0);

        /* 4-cmul */
        { int *prod=malloc(W*sizeof(int)); cmul_hl(f, v, w, prod, W); add_n(f, u, prod, u, W); free(prod); }
        { int *prod=malloc(W*sizeof(int)); cmul_hl(f, w, z, prod, W); add_n(f, v, prod, v, W); free(prod); }
        { int *prod=malloc(W*sizeof(int)); cmul_lh(f, u, v, prod, W); add_n(f, w, prod, w, W); free(prod); }
        { int *prod=malloc(W*sizeof(int)); cmul_hl(f, w, z, prod, W); add_n(f, u, prod, u, W); free(prod); }

        /* Post-ARX */
        { int *rv2=malloc(W*sizeof(int)),*add=malloc(W*sizeof(int));
          rotl_wire(v,rv2,19%W,W); add_n(f, rv2, w, add, W);
          for(int i=0;i<W;i++) u[i]=xor_gate(f, u[i], add[i]); free(rv2); free(add); }
        { int *rw2=malloc(W*sizeof(int)),*add=malloc(W*sizeof(int));
          rotl_wire(w,rw2,23%W,W); add_n(f, rw2, z, add, W);
          for(int i=0;i<W;i++) v[i]=xor_gate(f, v[i], add[i]); free(rw2); free(add); }
        { int *rz2=malloc(W*sizeof(int)),*add=malloc(W*sizeof(int));
          rotl_wire(z,rz2,7%W,W); add_n(f, rz2, u, add, W);
          for(int i=0;i<W;i++) w[i]=xor_gate(f, w[i], add[i]); free(rz2); free(add); }
        { int *ru2=malloc(W*sizeof(int)),*add=malloc(W*sizeof(int));
          rotl_wire(u,ru2,11%W,W); add_n(f, ru2, v, add, W);
          for(int i=0;i<W;i++) z[i]=xor_gate(f, z[i], add[i]); free(ru2); free(add); }
    }

    /* Output constraints: fix u[0..W-1] to known values */
    for (int i = 0; i < W; i++) {
        int known = (i * 7 + R * 13) & 1;
        cla1(f, known ? u[i] : -u[i]);
    }

    free(u); free(v); free(w); free(z);
    fclose(f);

    /* Prepend DIMACS header */
    FILE *in = fopen("_temp_cnf.cnf", "r");
    char outname[64]; snprintf(outname, sizeof(outname), "tempest_W%d_R%d.cnf", W, R);
    FILE *out = fopen(outname, "w");
    fprintf(out, "p cnf %d %d\n", nv, nc);
    char buf[4096];
    while (fgets(buf, sizeof(buf), in)) fputs(buf, out);
    fclose(in); fclose(out);
    remove("_temp_cnf.cnf");

    fprintf(stderr, "Generated: %s  Vars=%d  Clauses=%d\n", outname, nv, nc);
    return 0;
}
