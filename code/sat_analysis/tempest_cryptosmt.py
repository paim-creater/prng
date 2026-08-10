#!/usr/bin/env python3
"""Tempest v3 cipher definition for CryptoSMT"""
from parser import stpcommands
from ciphers.cipher import AbstractCipher
from ciphers import components

class TempestCipher(AbstractCipher):
    @property
    def name(self):
        return "tempest"

    def getFormatString(self):
        return ['u', 'v', 'w', 'z']

    def createSTP(self, filename, parameters):
        wordsize = parameters.get("wordsize", 64)
        rounds = parameters["rounds"]
        self.state_variables = [f"u0", f"v0", f"w0", f"z0"]

        with open(filename, 'w') as stp_file:
            # Header
            stp_file.write(f"% Tempest v3 w={wordsize} rounds={rounds}\n\n")

            # Variables for each round
            for i in range(rounds + 1):
                for var in ['u', 'v', 'w', 'z']:
                    stpcommands.setupVariables(stp_file, [f"{var}{i}"], wordsize)

            # Round function constraints
            for i in range(rounds):
                self._round_constraint(stp_file, i, wordsize)

            # Non-zero input
            stpcommands.assertNonZero(stp_file, ["u0", "v0", "w0", "z0"], wordsize)

            # Query
            stpcommands.setupQuery(stp_file)

    def _round_constraint(self, stp_file, r, W):
        u, v, w, z = f"u{r}", f"v{r}", f"w{r}", f"z{r}"
        un, vn, wn, zn = f"u{r+1}", f"v{r+1}", f"w{r+1}", f"z{r+1}"

        def rot(x, k):
            return f"BVXOR(BVLSHIFT({x}, {k}), BVRSHIFT({x}, {W - k}))" if k else x

        def xor(a, b):
            return f"BVXOR({a}, {b})"

        def andop(a, b):
            return f"BVAND({a}, {b})"

        # Phase B: 4-source XOR-ROT
        u1 = xor(xor(xor(u, rot(v, 7)), rot(w, 17)), rot(z, 23))
        v1 = xor(xor(xor(v, rot(w, 11)), rot(z, 13)), rot(u, 19))
        w1 = xor(xor(xor(w, rot(z, 13)), rot(u, 31)), rot(v, 11))
        z1 = xor(xor(xor(z, rot(u, 17)), rot(v, 7)), rot(w, 13))

        # Pre-mix: t ^= rotl(t,22) ^ rotl(t,26)
        def premix(t):
            return xor(xor(t, rot(t, 22)), rot(t, 26))

        # andmix4 (4 stages)
        def andmix4(t):
            for r1, r2 in [(31,53),(17,43),(7,23),(5,19)]:
                t = xor(t, andop(rot(t, r1), rot(t, r2)))
            return t

        u2 = andmix4(premix(u1))
        v2 = andmix4(premix(v1))
        w2 = andmix4(premix(w1))
        z2 = andmix4(premix(z1))

        # Phase D
        u3 = xor(xor(u2, rot(v2, 3)), rot(w2, 7))
        v3 = xor(xor(v2, rot(w2, 5)), rot(z2, 11))
        w3 = xor(xor(w2, rot(z2, 7)), rot(u2, 13))
        z3 = xor(xor(z2, rot(u2, 11)), rot(v2, 17))

        stp_file.write(f"ASSERT({un} = {u3});\n")
        stp_file.write(f"ASSERT({vn} = {v3});\n")
        stp_file.write(f"ASSERT({wn} = {w3});\n")
        stp_file.write(f"ASSERT({zn} = {z3});\n")
