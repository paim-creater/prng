/* bitgen_tempest.c — Tempest v3 NumPy BitGenerator (C 扩展)
 * ======================================================================
 * 将 Tempest v3 注册为 NumPy 的一等公民 BitGenerator,
 * 使 np.random.default_rng(TempestBitGenerator()) 直接可用。
 *
 * 编译:
 *   python setup_bitgen.py build_ext --inplace
 *
 * 使用:
 *   from bitgen_tempest import TempestBitGenerator
 *   rng = np.random.default_rng(TempestBitGenerator(seed=42))
 *   rng.normal(0, 1, 1000)
 *
 * 依赖:
 *   pip install numpy
 *   NumPy 开发头文件 (pip install numpy 后会自动包含)
 * ====================================================================== */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

/* ── Tempest v3 核心算法 (内联, 无需外部依赖) ── */
typedef struct {
    uint64_t u, v, w, z, rounds, weyl;
} TempestState;

#define ROTL(x, r) (((x) << (r)) | ((x) >> (64 - (r))))
#define WEYL_GOLDEN 0x9E3779B97F4A7C15ULL

static inline uint64_t cmul_hl(uint64_t a, uint64_t b) {
    return (uint64_t)(uint32_t)(a >> 32) * (uint64_t)(uint32_t)b;
}
static inline uint64_t cmul_lh(uint64_t a, uint64_t b) {
    return (uint64_t)(uint32_t)a * (uint64_t)(uint32_t)(b >> 32);
}

static void tempest_round(TempestState *s) {
    uint64_t u = s->u, v = s->v, w = s->w, z = s->z;
    int sh = (int)(s->rounds & 3);
    uint64_t wval = s->weyl;
    wval += WEYL_GOLDEN;
    u ^= ROTL(wval, 7) ^ (wval >> 17);
    v ^= ROTL(wval, 19) ^ (wval >> 23);
    w ^= ROTL(wval, 31) ^ (wval >> 29);
    z ^= ROTL(wval, 43) ^ (wval >> 37);
    s->weyl = wval;
    uint64_t u0 = u;
    u += ROTL(v, 7) ^ ROTL(z, 13);
    v += ROTL(w, 11);
    w += ROTL(z, 13);
    z += ROTL(u0, 17);
    u += cmul_hl(v, w); v += cmul_hl(w, z);
    w += cmul_lh(u, v); u += cmul_hl(w, z);
    u ^= ROTL(v, 19) + w; v ^= ROTL(w, 23) + z;
    w ^= ROTL(z, 7) + u; z ^= ROTL(u, 11) + v;
    if ((s->rounds & 1) == 0) {
        z ^= ROTL(v, (unsigned)(19 - sh * 2)) + u;
        w ^= ROTL(u, (unsigned)(23 - sh * 2)) + z;
        v ^= ROTL(z, (unsigned)(7 + sh * 2)) + w;
        u ^= ROTL(w, (unsigned)(11 + sh * 2)) + v;
    }
    s->u = u; s->v = v; s->w = w; s->z = z; s->rounds++;
}

static uint64_t make_output(uint64_t u, uint64_t v, uint64_t w, uint64_t z) {
    uint64_t t = u ^ ROTL(v, 32) ^ w ^ ROTL(z, 16);
    t ^= ROTL(t, 27);
    t ^= ROTL(t, 31) & ROTL(t, 53);
    t ^= ROTL(t, 17) & ROTL(t, 43);
    t ^= ROTL(t,  7) & ROTL(t, 23);
    t ^= ROTL(t,  5) & ROTL(t, 19);
    t ^= t >> 32;
    return t;
}

static uint64_t tempest_next(TempestState *s) {
    tempest_round(s);
    return make_output(s->u, s->v, s->w, s->z);
}

static void tempest_init(TempestState *s,
    const uint64_t key[4], const uint64_t nonce[2])
{
    uint64_t k0 = key[0], k1 = key[1], k2 = key[2], k3 = key[3];
    s->u = k0; s->v = k1 ^ nonce[0]; s->w = k2 ^ nonce[1];
    s->z = k3 ^ 0x54454D5035583543ULL; s->rounds = 0;
    s->weyl = 0x6A09E667F3BCC908ULL;
    uint64_t weyl = 0x6A09E667F3BCC908ULL;
    for (int i = 0; i < 16; i++) {
        tempest_round(s); weyl += WEYL_GOLDEN;
        if (i < 8) {
            if (i & 1) {
                s->u ^= ROTL(k0, (unsigned)(i + 1)) ^ weyl;
                s->v ^= ROTL(k1, (unsigned)(i + 1)) ^ (weyl << 17);
                s->w ^= ROTL(k2, (unsigned)(i + 1)) ^ (weyl >> 13);
                s->z ^= ROTL(k3, (unsigned)(i + 1)) ^ ROTL(weyl, 31);
            } else {
                s->u ^= k0 ^ weyl; s->v ^= k1 ^ (weyl << 17);
                s->w ^= k2 ^ (weyl >> 13); s->z ^= k3 ^ ROTL(weyl, 31);
            }
        } else {
            uint64_t nh = nonce[i & 1], nl = nonce[1 - (i & 1)];
            uint64_t nc = (nh << 32) | (uint32_t)nl;
            s->u ^= nc; s->v ^= ROTL(nc, 19) ^ (uint64_t)i;
            s->z ^= ROTL(nc, 43);
        }
    }
    for (int i = 0; i < 6; i++) tempest_round(s);
    s->u ^= k0; s->v ^= k1; s->w ^= k2; s->z ^= k3;
}

/* ═══════════════════════════════════════════════════════════════════════
 * NumPy BitGenerator 回调接口
 * ═══════════════════════════════════════════════════════════════════════ */

/* 从封装中提取状态指针 */
static TempestState *get_state(PyObject *capsule) {
    return (TempestState *)PyCapsule_GetPointer(capsule, NULL);
}

/* next_uint64 — NumPy BitGenerator 核心回调 */
static uint64_t cb_next_uint64(void *state) {
    return tempest_next((TempestState *)state);
}

/* next_uint32 — 取高 32 bit */
static uint32_t cb_next_uint32(void *state) {
    return (uint32_t)(tempest_next((TempestState *)state) >> 32);
}

/* next_double — float64 [0, 1) */
static double cb_next_double(void *state) {
    return (tempest_next((TempestState *)state) >> 11) * 0x1.0p-53;
}

/* reset_state — 重置状态 (保留完整 256 bit 熵) */
static void cb_reset_state(void *state) {
    TempestState *ts = (TempestState *)state;
    uint64_t key[4] = { ts->u, ts->v, ts->w, ts->z };
    uint64_t nonce[2] = { ts->rounds, ts->weyl };
    tempest_init(ts, key, nonce);
}

/* ═══════════════════════════════════════════════════════════════════════
 * Python 类型: TempestBitGenerator
 * ═══════════════════════════════════════════════════════════════════════ */
typedef struct {
    PyObject_HEAD
    TempestState state;
} TempestBitGenObject;

static PyObject *TempestBitGen_new(PyTypeObject *type,
    PyObject *args, PyObject *kwds)
{
    TempestBitGenObject *self;
    self = (TempestBitGenObject *)type->tp_alloc(type, 0);
    if (self) {
        memset(&self->state, 0, sizeof(self->state));
    }
    return (PyObject *)self;
}

static int TempestBitGen_init(PyObject *self, PyObject *args, PyObject *kwds) {
    TempestBitGenObject *obj = (TempestBitGenObject *)self;
    unsigned long long seed = 0;
    char *key_str = NULL;
    static char *kwlist[] = {"seed", "key", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|Kz", kwlist,
                                     &seed, &key_str))
        return -1;

    if (key_str && strlen(key_str) == 64) {
        /* Hex key: 64 hex chars = 256 bit */
        uint64_t key[4], nonce[2] = {0, 0};
        for (int i = 0; i < 4; i++) {
            key[i] = strtoull(key_str + i * 16, NULL, 16);
        }
        tempest_init(&obj->state, key, nonce);
    } else {
        /* 从 64-bit seed 派生 */
        uint64_t s = (uint64_t)seed;
        uint64_t key[4] = {
            s + WEYL_GOLDEN,
            ((s << 17) | (s >> 47)) * 0x6A09E667F3BCC909ULL,
            s ^ 0x3243F6A8885A308DULL,
            ((s << 32) | (s >> 32)) + 0xB7E151628AED2A6BULL
        };
        uint64_t nonce[2] = {0, 0};
        tempest_init(&obj->state, key, nonce);
    }
    return 0;
}

/* ═══════════════════════════════════════════════════════════════════════
 * `.capsule` 属性 — NumPy BitGenerator 所需的 Capsule
 * ═══════════════════════════════════════════════════════════════════════ */
static void capsule_free(PyObject *capsule) {
    /* 清理状态 (安全清零) */
    void *state = PyCapsule_GetPointer(capsule, NULL);
    if (state) {
        volatile uint64_t *p = (volatile uint64_t *)state;
        for (int i = 0; i < 6; i++) p[i] = 0;
    }
}

static PyObject *TempestBitGen_get_capsule(PyObject *self, void *closure) {
    TempestBitGenObject *obj = (TempestBitGenObject *)self;

    /* 分配 bitgen_t 结构 */
    PyCapsule_Destructor *bitgen = PyMem_Malloc(sizeof(
        struct { void *state; uint64_t (*next_uint64)(void*);
                 uint32_t (*next_uint32)(void*);
                 double (*next_double)(void*);
                 void (*reset_state)(void*); }
    ));

    if (!bitgen) {
        PyErr_SetString(PyExc_MemoryError, "无法分配 BitGenerator 结构");
        return NULL;
    }

    /* 填充 bitgen_t 字段 */
    struct {
        void *state;
        uint64_t (*next_uint64)(void*);
        uint32_t (*next_uint32)(void*);
        double (*next_double)(void*);
        void (*reset_state)(void*);
    } *bg = (void*)bitgen;

    bg->state = &obj->state;
    bg->next_uint64 = cb_next_uint64;
    bg->next_uint32 = cb_next_uint32;
    bg->next_double = cb_next_double;
    bg->reset_state = cb_reset_state;

    /* 创建 Capsule */
    return PyCapsule_New(bg, "numpy.random.bitgen", capsule_free);
}

static PyGetSetDef TempestBitGen_getset[] = {
    {"capsule", (getter)TempestBitGen_get_capsule, NULL,
     "NumPy BitGenerator capsule", NULL},
    {NULL} /* sentinel */
};

/* ═══════════════════════════════════════════════════════════════════════
 * 方法: get_state / set_state (序列化)
 * ═══════════════════════════════════════════════════════════════════════ */
static PyObject *TempestBitGen_get_state(PyObject *self, PyObject *args) {
    TempestBitGenObject *obj = (TempestBitGenObject *)self;
    return PyBytes_FromStringAndSize((const char *)&obj->state,
                                     sizeof(TempestState));
}

static PyObject *TempestBitGen_set_state(PyObject *self, PyObject *args) {
    TempestBitGenObject *obj = (TempestBitGenObject *)self;
    const char *buf;
    Py_ssize_t len;

    if (!PyArg_ParseTuple(args, "y#", &buf, &len))
        return NULL;
    if (len != sizeof(TempestState)) {
        PyErr_SetString(PyExc_ValueError, "状态长度错误");
        return NULL;
    }
    memcpy(&obj->state, buf, sizeof(TempestState));
    Py_RETURN_NONE;
}

static PyMethodDef TempestBitGen_methods[] = {
    {"get_state", TempestBitGen_get_state, METH_NOARGS,
     "返回序列化状态 (bytes)"},
    {"set_state", TempestBitGen_set_state, METH_VARARGS,
     "设置序列化状态"},
    {NULL} /* sentinel */
};

/* ═══════════════════════════════════════════════════════════════════════
 * 类型定义
 * ═══════════════════════════════════════════════════════════════════════ */
static PyTypeObject TempestBitGeneratorType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "bitgen_tempest.TempestBitGenerator",
    .tp_doc = "Tempest v3 CSPRNG — 2^128 security BitGenerator",
    .tp_basicsize = sizeof(TempestBitGenObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = TempestBitGen_new,
    .tp_init = TempestBitGen_init,
    .tp_getset = TempestBitGen_getset,
    .tp_methods = TempestBitGen_methods,
};

/* ═══════════════════════════════════════════════════════════════════════
 * 模块定义
 * ═══════════════════════════════════════════════════════════════════════ */
static PyMethodDef module_methods[] = {
    {NULL} /* sentinel */
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    .m_name = "bitgen_tempest",
    .m_doc = "Tempest v3 NumPy BitGenerator — 2^128 CSPRNG",
    .m_size = -1,
    .m_methods = module_methods,
};

PyMODINIT_FUNC PyInit_bitgen_tempest(void) {
    if (PyType_Ready(&TempestBitGeneratorType) < 0)
        return NULL;

    PyObject *m = PyModule_Create(&moduledef);
    if (!m) return NULL;

    Py_INCREF(&TempestBitGeneratorType);
    if (PyModule_AddObject(m, "TempestBitGenerator",
                           (PyObject *)&TempestBitGeneratorType) < 0) {
        Py_DECREF(&TempestBitGeneratorType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}
