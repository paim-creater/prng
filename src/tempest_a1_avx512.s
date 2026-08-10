	.file	"tempest_a1_avx512.c"
	.text
	.p2align 4
	.def	a1_round;	.scl	3;	.type	32;	.endef
	.seh_proc	a1_round
a1_round:
	subq	$808, %rsp
	.seh_stackalloc	808
	vmovups	%xmm6, 640(%rsp)
	.seh_savexmm	%xmm6, 640
	vmovups	%xmm7, 656(%rsp)
	.seh_savexmm	%xmm7, 656
	vmovups	%xmm8, 672(%rsp)
	.seh_savexmm	%xmm8, 672
	vmovups	%xmm9, 688(%rsp)
	.seh_savexmm	%xmm9, 688
	vmovups	%xmm10, 704(%rsp)
	.seh_savexmm	%xmm10, 704
	vmovups	%xmm11, 720(%rsp)
	.seh_savexmm	%xmm11, 720
	vmovups	%xmm12, 736(%rsp)
	.seh_savexmm	%xmm12, 736
	vmovups	%xmm13, 752(%rsp)
	.seh_savexmm	%xmm13, 752
	vmovups	%xmm14, 768(%rsp)
	.seh_savexmm	%xmm14, 768
	vmovups	%xmm15, 784(%rsp)
	.seh_savexmm	%xmm15, 784
	.seh_endprologue
	vmovdqu64	64(%rcx), %zmm3
	vmovdqu64	(%rcx), %zmm4
	movl	$1, %eax
	vmovdqu64	128(%rcx), %zmm2
	vmovdqu64	192(%rcx), %zmm5
	vpsllq	$15, %zmm3, %zmm0
	vmovdqu64	%zmm0, 192(%rsp)
	vmovdqu64	256(%rcx), %zmm0
	vpsrlq	$59, %zmm4, %zmm27
	vpsllq	$29, %zmm4, %zmm6
	vpsrlq	$49, %zmm3, %zmm1
	vpsllq	$17, %zmm4, %zmm13
	vpsrlq	$35, %zmm4, %zmm7
	vmovdqu64	%zmm27, 448(%rsp)
	vmovdqu32	.LC0(%rip), %zmm27
	vpsrlq	$55, %zmm4, %zmm9
	vpsrlq	$33, %zmm4, %zmm11
	vpsllq	$9, %zmm4, %zmm17
	vpsllq	$31, %zmm4, %zmm24
	vpsrlq	$53, %zmm2, %zmm29
	vpsrlq	$47, %zmm2, %zmm14
	vmovdqu64	%zmm6, 64(%rsp)
	vpsllq	$5, %zmm4, %zmm6
	vpsllq	$11, %zmm2, %zmm16
	vpsrlq	$43, %zmm2, %zmm15
	vmovdqu64	%zmm1, 128(%rsp)
	vpsllq	$21, %zmm2, %zmm12
	vpsllq	$17, %zmm2, %zmm26
	vpsllq	$53, %zmm2, %zmm25
	vmovdqu64	%zmm6, 512(%rsp)
	vpsrlq	$39, %zmm5, %zmm28
	vpsrlq	$41, %zmm5, %zmm30
	vpsllq	$25, %zmm5, %zmm18
	vmovdqu64	%zmm13, 384(%rsp)
	vpsllq	$23, %zmm5, %zmm19
	vpsrlq	$51, %zmm5, %zmm10
	vpsllq	$13, %zmm5, %zmm23
	vmovdqu64	%zmm7, (%rsp)
	vpsrlq	$47, %zmm4, %zmm7
	vpsrlq	$57, %zmm3, %zmm8
	vpsllq	$7, %zmm3, %zmm22
	vmovdqu64	%zmm12, 320(%rsp)
	vpsrlq	$11, %zmm2, %zmm12
	vpsllq	$5, %zmm3, %zmm20
	vpsrlq	$59, %zmm3, %zmm31
	vpsllq	$19, %zmm0, %zmm1
	vmovdqa32	%zmm1, %zmm6
	vpsrlq	$45, %zmm0, %zmm13
	vpsrlq	$37, %zmm3, %zmm21
	vmovdqu64	%zmm15, 256(%rsp)
	vpsllq	$27, %zmm3, %zmm15
	vpord	%zmm12, %zmm25, %zmm25
	vpxord	%zmm27, %zmm0, %zmm0
	vpternlogd	$86, %zmm0, %zmm13, %zmm6
	vpandd	%zmm27, %zmm6, %zmm0
	vmovdqu32	%zmm6, 256(%rcx)
	vpsrlq	$51, %zmm0, %zmm1
	vpsllq	$13, %zmm0, %zmm0
	vpternlogd	$86, %zmm6, %zmm1, %zmm0
	vpsrlq	$17, %zmm0, %zmm1
	vmovdqu64	%zmm1, 576(%rsp)
	vpsrlq	$57, %zmm0, %zmm13
	vpsllq	$7, %zmm0, %zmm1
	vpsrlq	$45, %zmm0, %zmm12
	vpternlogd	$150, 576(%rsp), %zmm27, %zmm4
	vpternlogd	$86, %zmm4, %zmm14, %zmm26
	vpsrlq	$29, %zmm0, %zmm14
	vmovdqa32	%zmm20, %zmm4
	vpternlogq	$150, .LC6(%rip){1to8}, %zmm14, %zmm2
	vpternlogd	$86, %zmm2, %zmm11, %zmm24
	vpsrlq	$37, %zmm0, %zmm11
	vmovdqu32	192(%rsp), %zmm2
	vpternlogq	$150, .LC7(%rip){1to8}, %zmm11, %zmm5
	vpternlogd	$86, %zmm24, %zmm10, %zmm23
	vpternlogd	$86, %zmm5, %zmm8, %zmm22
	vmovdqu32	384(%rsp), %zmm5
	vpord	128(%rsp), %zmm2, %zmm2
	vpternlogd	$86, %zmm26, %zmm31, %zmm4
	vpternlogd	$86, %zmm4, %zmm13, %zmm1
	vpsrlq	$23, %zmm0, %zmm13
	vpord	%zmm28, %zmm18, %zmm4
	vpternlogq	$150, .LC5(%rip){1to8}, %zmm13, %zmm3
	vpsllq	$31, %zmm0, %zmm13
	vpternlogd	$168, %zmm4, %zmm31, %zmm20
	vmovdqa32	%zmm19, %zmm4
	vmovdqa32	%zmm13, %zmm10
	vpternlogd	$86, %zmm3, %zmm30, %zmm19
	vmovdqa32	%zmm16, %zmm3
	vpternlogd	$168, %zmm2, %zmm9, %zmm17
	vpsrlq	$21, %zmm0, %zmm9
	vpternlogd	$168, %zmm25, %zmm30, %zmm4
	vpternlogd	$86, %zmm22, %zmm7, %zmm5
	vmovdqu32	320(%rsp), %zmm7
	vpternlogd	$150, %zmm4, %zmm20, %zmm1
	vpsllq	$19, %zmm0, %zmm4
	vpternlogd	$86, %zmm19, %zmm29, %zmm3
	vpsrlq	$45, %zmm1, %zmm13
	vpsrlq	$38, %zmm1, %zmm11
	vpsllq	$19, %zmm1, %zmm8
	vpternlogd	$86, %zmm3, %zmm12, %zmm4
	vpsrlq	$33, %zmm0, %zmm12
	vpsllq	$43, %zmm0, %zmm0
	vpternlogd	$86, %zmm5, %zmm9, %zmm0
	vpord	256(%rsp), %zmm7, %zmm7
	vmovdqa32	%zmm15, %zmm5
	vmovdqu32	64(%rsp), %zmm3
	vpord	%zmm13, %zmm8, %zmm8
	vpsrlq	$42, %zmm1, %zmm9
	vpsllq	$22, %zmm1, %zmm6
	vpternlogd	$86, %zmm23, %zmm12, %zmm10
	vpsrlq	$57, %zmm1, %zmm12
	vpord	(%rsp), %zmm3, %zmm3
	vpxord	%zmm17, %zmm10, %zmm2
	vpternlogd	$168, %zmm7, %zmm21, %zmm5
	vmovdqu32	512(%rsp), %zmm7
	vpord	448(%rsp), %zmm7, %zmm21
	vpternlogd	$168, %zmm3, %zmm29, %zmm16
	vpsllq	$26, %zmm1, %zmm7
	vpord	%zmm11, %zmm7, %zmm7
	vpxord	%zmm16, %zmm4, %zmm3
	vpternlogd	$86, %zmm7, %zmm9, %zmm6
	vpsrlq	$38, %zmm3, %zmm9
	vpsllq	$19, %zmm3, %zmm7
	vpsrlq	$57, %zmm3, %zmm11
	vpternlogd	$168, %zmm21, %zmm28, %zmm18
	vpternlogd	$150, %zmm18, %zmm5, %zmm0
	vpsllq	$7, %zmm1, %zmm5
	vpternlogd	$168, %zmm8, %zmm12, %zmm5
	vpsrlq	$45, %zmm3, %zmm12
	vpternlogd	$150, %zmm1, %zmm6, %zmm5
	vpord	%zmm12, %zmm7, %zmm7
	vpsllq	$26, %zmm3, %zmm6
	vpsrlq	$42, %zmm3, %zmm8
	vpord	%zmm9, %zmm6, %zmm6
	vpsllq	$7, %zmm3, %zmm1
	vpsllq	$22, %zmm3, %zmm3
	vpternlogd	$168, %zmm7, %zmm11, %zmm1
	vpternlogd	$86, %zmm6, %zmm8, %zmm3
	vpsrlq	$45, %zmm2, %zmm11
	vpsrlq	$38, %zmm2, %zmm8
	vpsllq	$19, %zmm2, %zmm6
	vpxord	%zmm3, %zmm1, %zmm1
	vpord	%zmm11, %zmm6, %zmm6
	vpsllq	$26, %zmm2, %zmm3
	vpord	%zmm8, %zmm3, %zmm3
	vpternlogd	$150, %zmm1, %zmm16, %zmm4
	vpsrlq	$57, %zmm2, %zmm9
	vpsrlq	$42, %zmm2, %zmm7
	vpsllq	$7, %zmm2, %zmm1
	vpsllq	$22, %zmm2, %zmm2
	vpternlogd	$168, %zmm6, %zmm9, %zmm1
	vpternlogd	$86, %zmm3, %zmm7, %zmm2
	vpsrlq	$45, %zmm0, %zmm11
	vpxord	%zmm2, %zmm1, %zmm1
	vpsrlq	$38, %zmm0, %zmm8
	vpsllq	$19, %zmm0, %zmm6
	vpsllq	$26, %zmm0, %zmm3
	vpord	%zmm11, %zmm6, %zmm6
	vpord	%zmm8, %zmm3, %zmm3
	vpternlogd	$150, %zmm1, %zmm17, %zmm10
	vpsrlq	$57, %zmm0, %zmm9
	vpsrlq	$42, %zmm0, %zmm7
	vpsllq	$7, %zmm0, %zmm2
	vpsllq	$22, %zmm0, %zmm1
	vpternlogd	$168, %zmm6, %zmm9, %zmm2
	vpternlogd	$86, %zmm3, %zmm7, %zmm1
	vpsrlq	$11, %zmm10, %zmm3
	vpsllq	$31, %zmm4, %zmm12
	vpsrlq	$45, %zmm4, %zmm13
	vpternlogd	$150, %zmm0, %zmm1, %zmm2
	vpsllq	$53, %zmm10, %zmm0
	vpord	%zmm3, %zmm0, %zmm0
	vpsrlq	$33, %zmm4, %zmm1
	vpsrlq	$21, %zmm2, %zmm6
	vpternlogd	$168, %zmm0, %zmm1, %zmm12
	vpsllq	$43, %zmm2, %zmm1
	vpord	%zmm6, %zmm1, %zmm1
	vpsrlq	$47, %zmm10, %zmm3
	vpsrlq	$41, %zmm5, %zmm6
	vpsllq	$17, %zmm10, %zmm8
	vpternlogd	$168, %zmm1, %zmm3, %zmm8
	vpsllq	$23, %zmm5, %zmm1
	vpord	%zmm6, %zmm1, %zmm1
	vpsllq	$19, %zmm4, %zmm6
	vpord	%zmm13, %zmm6, %zmm6
	vpsrlq	$57, %zmm2, %zmm3
	vpsrlq	$59, %zmm5, %zmm11
	vpsllq	$7, %zmm2, %zmm9
	vpternlogd	$168, %zmm1, %zmm3, %zmm9
	vpsllq	$5, %zmm5, %zmm1
	vpternlogd	$168, %zmm6, %zmm11, %zmm1
	vpxord	%zmm4, %zmm8, %zmm7
	vpxord	%zmm5, %zmm12, %zmm0
	vpxord	%zmm2, %zmm1, %zmm6
	vpsrlq	$47, %zmm7, %zmm14
	vpsllq	$17, %zmm7, %zmm11
	vpsrlq	$21, %zmm6, %zmm15
	vpsllq	$43, %zmm6, %zmm13
	vpord	%zmm15, %zmm13, %zmm13
	vpxord	%zmm10, %zmm9, %zmm3
	vpternlogd	$168, %zmm13, %zmm14, %zmm11
	vpsrlq	$41, %zmm0, %zmm14
	vpsrlq	$57, %zmm3, %zmm13
	vpternlogd	$150, %zmm11, %zmm5, %zmm12
	vpsllq	$23, %zmm0, %zmm11
	vpord	%zmm14, %zmm11, %zmm11
	vpsllq	$7, %zmm3, %zmm5
	vpternlogd	$168, %zmm11, %zmm13, %zmm5
	vpternlogd	$150, %zmm5, %zmm4, %zmm8
	vpsrlq	$45, %zmm7, %zmm5
	vpsllq	$19, %zmm7, %zmm7
	vpord	%zmm5, %zmm7, %zmm7
	vpsrlq	$59, %zmm6, %zmm4
	vpsllq	$5, %zmm6, %zmm6
	vpternlogd	$168, %zmm7, %zmm4, %zmm6
	vpsrlq	$11, %zmm3, %zmm5
	vmovdqa32	%zmm9, %zmm7
	vpsllq	$53, %zmm3, %zmm3
	vpord	%zmm5, %zmm3, %zmm3
	vpsrlq	$33, %zmm0, %zmm4
	vpsllq	$31, %zmm0, %zmm0
	vpternlogd	$168, %zmm3, %zmm4, %zmm0
	vpsrlq	$50, %zmm12, %zmm3
	vpsllq	$16, %zmm8, %zmm11
	vpternlogd	$150, %zmm0, %zmm2, %zmm1
	vpsllq	$14, %zmm12, %zmm0
	vpord	%zmm3, %zmm0, %zmm0
	vpsrlq	$48, %zmm12, %zmm2
	vpsrlq	$50, %zmm8, %zmm3
	vpsrlq	$50, %zmm1, %zmm13
	vpternlogd	$150, %zmm6, %zmm10, %zmm7
	vpsllq	$16, %zmm12, %zmm10
	vpternlogd	$86, %zmm0, %zmm2, %zmm10
	vpsllq	$14, %zmm8, %zmm0
	vpord	%zmm3, %zmm0, %zmm0
	vpsrlq	$48, %zmm8, %zmm2
	vpsrlq	$50, %zmm7, %zmm3
	vpxord	%zmm12, %zmm10, %zmm5
	vpternlogd	$86, %zmm0, %zmm2, %zmm11
	vpsllq	$14, %zmm7, %zmm0
	vpord	%zmm3, %zmm0, %zmm0
	vpsllq	$14, %zmm1, %zmm3
	vpord	%zmm13, %zmm3, %zmm3
	vpsrlq	$48, %zmm7, %zmm2
	vpsrlq	$48, %zmm1, %zmm6
	vpsllq	$16, %zmm7, %zmm9
	vpternlogd	$86, %zmm0, %zmm2, %zmm9
	vpsllq	$16, %zmm1, %zmm0
	vpternlogd	$86, %zmm3, %zmm6, %zmm0
	vpsrlq	$41, %zmm5, %zmm15
	vpxord	%zmm1, %zmm0, %zmm3
	vpsllq	$23, %zmm5, %zmm13
	vpord	%zmm15, %zmm13, %zmm13
	vpxord	%zmm8, %zmm11, %zmm4
	vpsrlq	$57, %zmm3, %zmm14
	vpsllq	$7, %zmm3, %zmm6
	vpternlogd	$168, %zmm13, %zmm14, %zmm6
	vpternlogd	$150, %zmm6, %zmm12, %zmm10
	vpsrlq	$45, %zmm4, %zmm13
	vpsllq	$19, %zmm4, %zmm6
	vpord	%zmm13, %zmm6, %zmm6
	vpxord	%zmm7, %zmm9, %zmm2
	vpsrlq	$59, %zmm5, %zmm12
	vpsllq	$5, %zmm5, %zmm5
	vpternlogd	$168, %zmm6, %zmm12, %zmm5
	vpternlogd	$150, %zmm5, %zmm8, %zmm11
	vpsrlq	$11, %zmm2, %zmm8
	vpsllq	$53, %zmm2, %zmm5
	vpord	%zmm8, %zmm5, %zmm5
	vpsrlq	$33, %zmm4, %zmm6
	vpsllq	$31, %zmm4, %zmm4
	vpternlogd	$168, %zmm5, %zmm6, %zmm4
	vpsrlq	$21, %zmm3, %zmm5
	vpsllq	$43, %zmm3, %zmm3
	vpord	%zmm5, %zmm3, %zmm3
	vpternlogd	$150, %zmm4, %zmm7, %zmm9
	vpsrlq	$47, %zmm2, %zmm4
	vpsllq	$17, %zmm2, %zmm2
	vpternlogd	$168, %zmm3, %zmm4, %zmm2
	vpsrlq	$45, %zmm9, %zmm3
	vpsllq	$5, %zmm11, %zmm8
	vpternlogd	$150, %zmm2, %zmm1, %zmm0
	vpsllq	$19, %zmm9, %zmm1
	vpord	%zmm3, %zmm1, %zmm1
	vpsrlq	$59, %zmm11, %zmm2
	vpsrlq	$11, %zmm0, %zmm4
	vpternlogd	$168, %zmm1, %zmm2, %zmm8
	vpsllq	$53, %zmm0, %zmm2
	vpord	%zmm4, %zmm2, %zmm2
	vpsrlq	$33, %zmm9, %zmm3
	vpsllq	$31, %zmm9, %zmm7
	vpsrlq	$11, %zmm10, %zmm5
	vpternlogd	$168, %zmm2, %zmm3, %zmm7
	vpsllq	$53, %zmm10, %zmm3
	vpord	%zmm5, %zmm3, %zmm3
	vpsrlq	$47, %zmm0, %zmm4
	vpsllq	$17, %zmm0, %zmm6
	vpternlogd	$168, %zmm3, %zmm4, %zmm6
	vpxord	%zmm11, %zmm7, %zmm2
	vpsrlq	$41, %zmm11, %zmm13
	vpsllq	$23, %zmm11, %zmm3
	vpxord	%zmm9, %zmm6, %zmm4
	vpord	%zmm13, %zmm3, %zmm3
	vpsrlq	$61, %zmm2, %zmm14
	vpsrlq	$57, %zmm10, %zmm12
	vpsrlq	$55, %zmm4, %zmm15
	vpsllq	$9, %zmm4, %zmm13
	vpord	%zmm15, %zmm13, %zmm13
	vpsllq	$7, %zmm10, %zmm5
	vpternlogd	$168, %zmm3, %zmm12, %zmm5
	vpsllq	$3, %zmm2, %zmm12
	vpternlogd	$86, %zmm13, %zmm14, %zmm12
	vpxord	%zmm10, %zmm8, %zmm1
	vpxord	%zmm0, %zmm5, %zmm3
	vpternlogd	$150, %zmm12, %zmm10, %zmm8
	vpsrlq	$53, %zmm3, %zmm12
	vpsrlq	$59, %zmm4, %zmm10
	vpsllq	$5, %zmm4, %zmm4
	vmovdqu32	%zmm8, (%rcx)
	vpsllq	$11, %zmm3, %zmm8
	vpord	%zmm12, %zmm8, %zmm8
	vpternlogd	$86, %zmm8, %zmm10, %zmm4
	vpsrlq	$51, %zmm1, %zmm8
	vpternlogd	$150, %zmm4, %zmm11, %zmm7
	vpsllq	$13, %zmm1, %zmm4
	vpord	%zmm8, %zmm4, %zmm4
	vmovdqu32	%zmm7, 64(%rcx)
	vpsrlq	$55, %zmm3, %zmm7
	vpsllq	$9, %zmm3, %zmm3
	vpternlogd	$86, %zmm4, %zmm7, %zmm3
	vpsrlq	$47, %zmm2, %zmm4
	vpsllq	$17, %zmm2, %zmm2
	vpord	%zmm4, %zmm2, %zmm2
	vpternlogd	$150, %zmm3, %zmm9, %zmm6
	vpsrlq	$53, %zmm1, %zmm3
	vpsllq	$11, %zmm1, %zmm1
	vpternlogd	$86, %zmm2, %zmm3, %zmm1
	vmovdqu32	%zmm6, 128(%rcx)
	vpternlogd	$150, %zmm1, %zmm0, %zmm5
	vpbroadcastq	%rax, %zmm0
	vpaddq	384(%rcx), %zmm0, %zmm0
	vmovdqu32	%zmm5, 192(%rcx)
	vmovdqu64	%zmm0, 384(%rcx)
	vzeroupper
	vmovups	640(%rsp), %xmm6
	vmovups	656(%rsp), %xmm7
	vmovups	672(%rsp), %xmm8
	vmovups	688(%rsp), %xmm9
	vmovups	704(%rsp), %xmm10
	vmovups	720(%rsp), %xmm11
	vmovups	736(%rsp), %xmm12
	vmovups	752(%rsp), %xmm13
	vmovups	768(%rsp), %xmm14
	vmovups	784(%rsp), %xmm15
	addq	$808, %rsp
	ret
	.seh_endproc
	.p2align 4
	.def	a1_output;	.scl	3;	.type	32;	.endef
	.seh_proc	a1_output
a1_output:
	.seh_endprologue
	movq	%rcx, %rax
	movq	40(%rsp), %rcx
	vmovdqu64	(%r8), %zmm0
	vmovdqu64	(%rcx), %zmm1
	vpsrlq	$32, %zmm0, %zmm2
	vpsllq	$32, %zmm0, %zmm0
	vpsrlq	$48, %zmm1, %zmm3
	vpsllq	$16, %zmm1, %zmm1
	vpord	%zmm3, %zmm1, %zmm1
	vmovdqu32	(%r9), %zmm3
	vpternlogd	$150, (%rdx), %zmm3, %zmm1
	vpternlogd	$86, %zmm1, %zmm2, %zmm0
	vpsrlq	$38, %zmm0, %zmm4
	vpsllq	$26, %zmm0, %zmm2
	vpord	%zmm4, %zmm2, %zmm2
	vpsrlq	$42, %zmm0, %zmm3
	vpsllq	$22, %zmm0, %zmm1
	vpternlogd	$86, %zmm2, %zmm3, %zmm1
	vpxord	%zmm0, %zmm1, %zmm2
	vpsrlq	$50, %zmm2, %zmm5
	vpsllq	$14, %zmm2, %zmm3
	vpord	%zmm5, %zmm3, %zmm3
	vpsrlq	$48, %zmm2, %zmm4
	vpsllq	$16, %zmm2, %zmm2
	vpternlogd	$86, %zmm3, %zmm4, %zmm2
	vpternlogd	$150, %zmm2, %zmm0, %zmm1
	vpsrlq	$11, %zmm1, %zmm4
	vpsllq	$53, %zmm1, %zmm2
	vpord	%zmm4, %zmm2, %zmm2
	vpsrlq	$33, %zmm1, %zmm3
	vpsllq	$31, %zmm1, %zmm0
	vpternlogd	$168, %zmm2, %zmm3, %zmm0
	vpxord	%zmm1, %zmm0, %zmm2
	vpsrlq	$21, %zmm2, %zmm5
	vpsllq	$43, %zmm2, %zmm3
	vpord	%zmm5, %zmm3, %zmm3
	vpsrlq	$47, %zmm2, %zmm4
	vpsllq	$17, %zmm2, %zmm2
	vpternlogd	$168, %zmm3, %zmm4, %zmm2
	vpternlogd	$150, %zmm2, %zmm1, %zmm0
	vpsrlq	$41, %zmm0, %zmm4
	vpsllq	$23, %zmm0, %zmm2
	vpord	%zmm4, %zmm2, %zmm2
	vpsrlq	$57, %zmm0, %zmm3
	vpsllq	$7, %zmm0, %zmm1
	vpternlogd	$168, %zmm2, %zmm3, %zmm1
	vpxord	%zmm0, %zmm1, %zmm2
	vpsrlq	$45, %zmm2, %zmm5
	vpsllq	$19, %zmm2, %zmm3
	vpord	%zmm5, %zmm3, %zmm3
	vpsrlq	$59, %zmm2, %zmm4
	vpsllq	$5, %zmm2, %zmm2
	vpternlogd	$168, %zmm3, %zmm4, %zmm2
	vpternlogd	$150, %zmm2, %zmm0, %zmm1
	vpsrlq	$32, %zmm1, %zmm0
	vpxord	%zmm0, %zmm1, %zmm1
	vmovdqu32	%zmm1, (%rax)
	vzeroupper
	ret
	.seh_endproc
	.p2align 4
	.def	now_ms;	.scl	3;	.type	32;	.endef
	.seh_proc	now_ms
now_ms:
	subq	$72, %rsp
	.seh_stackalloc	72
	vmovups	%xmm6, 48(%rsp)
	.seh_savexmm	%xmm6, 48
	.seh_endprologue
	vxorps	%xmm6, %xmm6, %xmm6
	leaq	32(%rsp), %rcx
	call	*__imp_QueryPerformanceFrequency(%rip)
	leaq	40(%rsp), %rcx
	call	*__imp_QueryPerformanceCounter(%rip)
	vcvtsi2sdq	40(%rsp), %xmm6, %xmm0
	vmulsd	.LC8(%rip), %xmm0, %xmm0
	vcvtsi2sdq	32(%rsp), %xmm6, %xmm6
	vdivsd	%xmm6, %xmm0, %xmm0
	vmovups	48(%rsp), %xmm6
	addq	$72, %rsp
	ret
	.seh_endproc
	.section .rdata,"dr"
.LC13:
	.ascii "PASS\0"
.LC14:
	.ascii "FAIL\0"
.LC24:
	.ascii "KAT %d stream %d FAIL\12\0"
	.align 8
.LC25:
	.ascii "KAT (8 streams, Algorithm-1): %s\12\0"
	.align 8
.LC29:
	.ascii "freq=%.3f GHz  AVX-512 dual (8 streams): %.1f Gbit/s  (->5GHz: %.1f)\12\0"
	.section	.text.startup,"x"
	.p2align 4
	.globl	main
	.def	main;	.scl	2;	.type	32;	.endef
	.seh_proc	main
main:
	pushq	%r12
	.seh_pushreg	%r12
	pushq	%rbp
	.seh_pushreg	%rbp
	pushq	%rdi
	.seh_pushreg	%rdi
	pushq	%rsi
	.seh_pushreg	%rsi
	pushq	%rbx
	.seh_pushreg	%rbx
	subq	$1824, %rsp
	.seh_stackalloc	1824
	vmovups	%xmm6, 1792(%rsp)
	.seh_savexmm	%xmm6, 1792
	vmovups	%xmm7, 1808(%rsp)
	.seh_savexmm	%xmm7, 1808
	.seh_endprologue
	movl	$1, %eax
	leaq	1359(%rsp), %rbx
	vpbroadcastq	%rax, %zmm5
	movl	$7, %eax
	andq	$-64, %rbx
	vpbroadcastq	%rax, %zmm6
	movl	$5, %eax
	vpbroadcastq	%rax, %zmm0
	vmovdqu64	%zmm5, 720(%rsp)
	vmovdqu64	%zmm6, 656(%rsp)
	vmovdqu64	%zmm0, 592(%rsp)
	vzeroupper
	call	__main
	vmovdqu64	.LC15(%rip), %zmm0
	vmovdqu64	.LC12(%rip), %zmm18
	xorl	%r10d, %r10d
	vmovdqu64	592(%rsp), %zmm5
	vmovdqu64	656(%rsp), %zmm1
	vmovdqu64	720(%rsp), %zmm17
	vmovdqu64	%zmm0, 1168(%rsp)
	vmovdqu64	%zmm0, 1232(%rsp)
	vpxor	%xmm0, %xmm0, %xmm0
	vmovdqu64	%zmm0, 384(%rbx)
	vmovdqu64	.LC9(%rip), %zmm0
	vmovdqu64	%zmm18, 256(%rbx)
	jmp	.L9
	.p2align 4
	.p2align 3
.L37:
	movl	$64, %edi
	movl	$4, %edx
	vmovd	%eax, %xmm16
	vpxord	%zmm1, %zmm0, %zmm1
	subl	%eax, %edi
	vpbroadcastq	%rdx, %zmm20
	movl	$3, %edx
	vmovq	%rdi, %xmm3
	movl	$1, %edi
	vpbroadcastq	%rdx, %zmm21
	vpbroadcastq	%rdi, %zmm6
	movl	$2, %edx
	vpbroadcastq	%rdx, %zmm22
	vmovdqu64	%zmm20, 432(%rsp)
	vpsrlq	%xmm3, %zmm6, %zmm2
	vpsllq	%xmm16, %zmm6, %zmm17
	vpsllq	$17, %zmm0, %zmm6
	vpxord	%zmm6, %zmm5, %zmm5
	vpsrlq	$13, %zmm0, %zmm6
	vpxord	%zmm6, %zmm4, %zmm4
	vmovdqu64	%zmm21, 368(%rsp)
	vpternlogd	$86, %zmm1, %zmm2, %zmm17
	vpsrlq	%xmm3, %zmm22, %zmm2
	vpsllq	%xmm16, %zmm22, %zmm1
	vpternlogd	$86, %zmm5, %zmm2, %zmm1
	vpsrlq	%xmm3, %zmm21, %zmm2
	vpsllq	%xmm16, %zmm21, %zmm5
	vpsrlq	%xmm3, %zmm20, %zmm3
	vpternlogd	$86, %zmm4, %zmm2, %zmm5
	vpsllq	%xmm16, %zmm20, %zmm2
	vpord	%zmm3, %zmm2, %zmm2
	vpsrlq	$33, %zmm0, %zmm4
	vpsllq	$31, %zmm0, %zmm0
	vmovdqu64	%zmm22, 304(%rsp)
	vpternlogd	$86, %zmm2, %zmm4, %zmm0
	vpxord	%zmm19, %zmm0, %zmm0
	cmpl	$8, %eax
	je	.L36
.L7:
	movl	%eax, %r10d
.L9:
	vmovdqu64	%zmm18, 48(%rsp)
	movq	%rbx, %rcx
	vmovdqu64	%zmm1, 64(%rbx)
	vmovdqu64	%zmm5, 128(%rbx)
	vmovdqu64	%zmm0, 192(%rbx)
	vmovdqu64	%zmm17, (%rbx)
	vzeroupper
	call	a1_round
	vmovdqu64	48(%rsp), %zmm18
	vmovdqu32	64(%rbx), %zmm5
	leal	1(%r10), %eax
	vmovdqu32	192(%rbx), %zmm19
	vmovdqu32	128(%rbx), %zmm4
	vpsrlq	$45, %zmm18, %zmm1
	vpsllq	$19, %zmm18, %zmm0
	vpxord	.LC0(%rip), %zmm18, %zmm18
	vpternlogd	$86, %zmm18, %zmm1, %zmm0
	vmovdqu32	(%rbx), %zmm1
	vmovdqa64	%zmm0, %zmm18
	andl	$1, %r10d
	jne	.L37
	vmovdqu32	.LC19(%rip), %zmm6
	vpsllq	$17, %zmm0, %zmm2
	vpsrlq	$33, %zmm0, %zmm3
	vpternlogd	$150, %zmm0, %zmm6, %zmm1
	vmovdqu32	.LC20(%rip), %zmm6
	vmovdqa32	%zmm1, %zmm17
	vpternlogd	$150, %zmm2, %zmm6, %zmm5
	vpsrlq	$13, %zmm0, %zmm2
	vpsllq	$31, %zmm0, %zmm0
	vmovdqa32	%zmm5, %zmm1
	vmovdqu32	.LC21(%rip), %zmm5
	vpternlogd	$150, %zmm2, %zmm5, %zmm4
	vpxord	.LC22(%rip), %zmm19, %zmm2
	vmovdqa32	%zmm4, %zmm5
	vpternlogd	$86, %zmm2, %zmm3, %zmm0
	jmp	.L7
.L36:
	movl	$8, %edx
	.p2align 4
	.p2align 3
.L8:
	vmovdqu64	%zmm17, (%rbx)
	movq	%rbx, %rcx
	vmovdqu64	%zmm1, 64(%rbx)
	vmovdqu64	%zmm5, 128(%rbx)
	vmovdqu64	%zmm0, 192(%rbx)
	vzeroupper
	call	a1_round
	movq	%rdx, %rax
	vmovdqu64	128(%rbx), %zmm5
	andl	$1, %eax
	vmovq	1264(%rsp,%rax,8), %xmm6
	vpinsrq	$1, 1280(%rsp,%rax,8), %xmm6, %xmm0
	vmovq	1232(%rsp,%rax,8), %xmm6
	vpinsrq	$1, 1248(%rsp,%rax,8), %xmm6, %xmm1
	vmovq	1200(%rsp,%rax,8), %xmm6
	vpinsrq	$1, 1216(%rsp,%rax,8), %xmm6, %xmm2
	vmovq	1168(%rsp,%rax,8), %xmm6
	vinserti64x2	$0x1, %xmm0, %ymm1, %ymm1
	vpinsrq	$1, 1184(%rsp,%rax,8), %xmm6, %xmm0
	movl	%edx, %eax
	notl	%eax
	andl	$1, %eax
	vmovq	1264(%rsp,%rax,8), %xmm6
	vinserti64x2	$0x1, %xmm2, %ymm0, %ymm0
	vinserti64x4	$0x1, %ymm1, %zmm0, %zmm0
	vpinsrq	$1, 1280(%rsp,%rax,8), %xmm6, %xmm1
	vmovq	1232(%rsp,%rax,8), %xmm6
	vpinsrq	$1, 1248(%rsp,%rax,8), %xmm6, %xmm2
	vmovq	1200(%rsp,%rax,8), %xmm6
	vpinsrq	$1, 1216(%rsp,%rax,8), %xmm6, %xmm3
	vmovq	1168(%rsp,%rax,8), %xmm6
	vpxord	(%rbx), %zmm0, %zmm17
	vinserti64x2	$0x1, %xmm1, %ymm2, %ymm2
	vpinsrq	$1, 1184(%rsp,%rax,8), %xmm6, %xmm1
	vinserti64x2	$0x1, %xmm3, %ymm1, %ymm1
	vinserti64x4	$0x1, %ymm2, %zmm1, %zmm1
	vpsrlq	$45, %zmm1, %zmm2
	vpsllq	$19, %zmm1, %zmm1
	vpternlogd	$86, 64(%rbx), %zmm2, %zmm1
	vpbroadcastq	%rdx, %zmm2
	incq	%rdx
	vpxord	%zmm2, %zmm1, %zmm1
	vpsrlq	$21, %zmm0, %zmm2
	vpsllq	$43, %zmm0, %zmm0
	vpternlogd	$86, 192(%rbx), %zmm2, %zmm0
	cmpq	$16, %rdx
	jne	.L8
	movl	$6, %edx
	.p2align 4
	.p2align 3
.L10:
	vmovdqu64	%zmm17, (%rbx)
	movq	%rbx, %rcx
	vmovdqu64	%zmm1, 64(%rbx)
	vmovdqu64	%zmm5, 128(%rbx)
	vmovdqu64	%zmm0, 192(%rbx)
	vzeroupper
	call	a1_round
	vmovdqu64	(%rbx), %zmm17
	vmovdqu64	64(%rbx), %zmm1
	vmovdqu64	128(%rbx), %zmm5
	vmovdqu64	192(%rbx), %zmm0
	decl	%edx
	jne	.L10
	vpxord	.LC19(%rip), %zmm17, %zmm6
	vpxord	.LC21(%rip), %zmm5, %zmm5
	movabsq	$9176669016871259524, %rax
	leaq	1120(%rsp), %rbp
	movq	%rax, 1152(%rsp)
	xorl	%edi, %edi
	leaq	784(%rsp), %rsi
	vmovdqu32	%zmm6, 48(%rsp)
	vpxord	.LC20(%rip), %zmm1, %zmm6
	vmovdqu32	%zmm5, 112(%rsp)
	vpxord	.LC22(%rip), %zmm0, %zmm5
	vmovdqu	.LC23(%rip), %ymm0
	vmovdqu32	%zmm6, 240(%rsp)
	vmovdqu32	%zmm5, 176(%rsp)
	vmovdqu	%ymm0, 1120(%rsp)
.L19:
	vmovdqu64	48(%rsp), %zmm6
	vmovdqu64	112(%rsp), %zmm5
	movq	%rbx, %rcx
	leaq	848(%rsp), %r9
	leaq	912(%rsp), %r8
	leaq	976(%rsp), %rdx
	vmovdqu64	%zmm6, (%rbx)
	vmovdqu64	240(%rsp), %zmm6
	vmovdqu64	%zmm5, 128(%rbx)
	vmovdqu64	%zmm6, 64(%rbx)
	vmovdqu64	176(%rsp), %zmm6
	vmovdqu64	%zmm6, 192(%rbx)
	vzeroupper
	call	a1_round
	vmovdqu64	128(%rbx), %zmm1
	vmovdqu64	192(%rbx), %zmm0
	leaq	1040(%rsp), %rcx
	vmovdqu64	(%rbx), %zmm5
	vmovdqu64	64(%rbx), %zmm6
	movq	%rsi, 32(%rsp)
	vmovdqu64	%zmm1, 112(%rsp)
	vmovdqu64	%zmm0, 176(%rsp)
	vmovdqu64	%zmm1, 848(%rsp)
	vmovdqu64	%zmm0, 784(%rsp)
	vmovdqu64	%zmm5, 48(%rsp)
	vmovdqu64	%zmm6, 240(%rsp)
	vmovdqu64	%zmm5, 976(%rsp)
	vmovdqu64	%zmm6, 912(%rsp)
	vzeroupper
	call	a1_output
	vmovdqu64	1040(%rsp), %zmm1
	movq	0(%rbp), %r12
	vmovq	%xmm1, %rax
	vmovdqa	%ymm1, %ymm0
	cmpq	%rax, %r12
	je	.L11
	vmovdqu64	%zmm1, 496(%rsp)
	vmovdqu	%ymm1, 560(%rsp)
	xorl	%r8d, %r8d
	movl	%edi, %edx
	leaq	.LC24(%rip), %rcx
	vzeroupper
	call	__mingw_printf
	vmovdqu64	496(%rsp), %zmm1
	vmovdqu	560(%rsp), %ymm0
	xorl	%r10d, %r10d
.L11:
	vpextrq	$1, %xmm0, %rax
	cmpq	%rax, %r12
	je	.L12
	vmovdqu64	%zmm1, 496(%rsp)
	vmovdqu	%ymm0, 560(%rsp)
	movl	$1, %r8d
	movl	%edi, %edx
	leaq	.LC24(%rip), %rcx
	vzeroupper
	call	__mingw_printf
	vmovdqu64	496(%rsp), %zmm1
	vmovdqu	560(%rsp), %ymm0
	xorl	%r10d, %r10d
.L12:
	vextracti64x2	$1, %ymm0, %xmm5
	vmovq	%xmm5, %rax
	cmpq	%rax, %r12
	je	.L13
	vmovdqu64	%zmm1, 496(%rsp)
	vmovdqu	%ymm0, 560(%rsp)
	movl	$2, %r8d
	movl	%edi, %edx
	leaq	.LC24(%rip), %rcx
	vzeroupper
	call	__mingw_printf
	vmovdqu64	496(%rsp), %zmm1
	vmovdqu	560(%rsp), %ymm0
	xorl	%r10d, %r10d
.L13:
	valignq	$3, %ymm0, %ymm0, %ymm0
	vmovq	%xmm0, %rax
	cmpq	%rax, %r12
	je	.L14
	vmovdqu64	%zmm1, 496(%rsp)
	movl	$3, %r8d
	movl	%edi, %edx
	leaq	.LC24(%rip), %rcx
	vzeroupper
	call	__mingw_printf
	vmovdqu64	496(%rsp), %zmm1
	xorl	%r10d, %r10d
.L14:
	vextracti64x4	$0x1, %zmm1, %ymm0
	vextracti64x2	$2, %zmm1, %xmm1
	vmovq	%xmm1, %rax
	cmpq	%rax, %r12
	je	.L15
	vmovdqu	%ymm0, 496(%rsp)
	movl	$4, %r8d
	movl	%edi, %edx
	leaq	.LC24(%rip), %rcx
	vzeroupper
	call	__mingw_printf
	vmovdqu	496(%rsp), %ymm0
	xorl	%r10d, %r10d
.L15:
	vpextrq	$1, %xmm0, %rax
	cmpq	%rax, %r12
	je	.L16
	vmovdqu	%ymm0, 496(%rsp)
	movl	$5, %r8d
	movl	%edi, %edx
	leaq	.LC24(%rip), %rcx
	vzeroupper
	call	__mingw_printf
	vmovdqu	496(%rsp), %ymm0
	xorl	%r10d, %r10d
.L16:
	vextracti64x2	$1, %ymm0, %xmm6
	vmovq	%xmm6, %rax
	cmpq	%rax, %r12
	je	.L17
	vmovdqu	%ymm0, 496(%rsp)
	movl	$6, %r8d
	movl	%edi, %edx
	leaq	.LC24(%rip), %rcx
	vzeroupper
	call	__mingw_printf
	vmovdqu	496(%rsp), %ymm0
	xorl	%r10d, %r10d
.L17:
	valignq	$3, %ymm0, %ymm0, %ymm0
	vmovq	%xmm0, %rax
	cmpq	%rax, %r12
	je	.L18
	movl	$7, %r8d
	movl	%edi, %edx
	leaq	.LC24(%rip), %rcx
	vzeroupper
	call	__mingw_printf
	xorl	%r10d, %r10d
.L18:
	incl	%edi
	addq	$8, %rbp
	cmpl	$5, %edi
	jne	.L19
	testl	%r10d, %r10d
	leaq	.LC13(%rip), %rax
	leaq	.LC14(%rip), %rdx
	leaq	.LC25(%rip), %rcx
	cmovne	%rax, %rdx
	vzeroupper
	call	__mingw_printf
	vmovdqu64	.LC12(%rip), %zmm18
	vpxor	%xmm0, %xmm0, %xmm0
	movq	$0, 1112(%rsp)
	vmovdqu64	592(%rsp), %zmm3
	xorl	%edx, %edx
	vmovdqu64	656(%rsp), %zmm2
	vmovdqu64	720(%rsp), %zmm17
	vmovdqu64	%zmm0, 384(%rbx)
	vmovdqu64	.LC9(%rip), %zmm0
	vmovdqu64	%zmm18, 256(%rbx)
	.p2align 4
	.p2align 3
.L24:
	vmovdqu64	%zmm18, 48(%rsp)
	movq	%rbx, %rcx
	vmovdqu64	%zmm2, 64(%rbx)
	vmovdqu64	%zmm3, 128(%rbx)
	vmovdqu64	%zmm0, 192(%rbx)
	vmovdqu64	%zmm17, (%rbx)
	vzeroupper
	call	a1_round
	vmovdqu64	48(%rsp), %zmm18
	leal	1(%rdx), %eax
	andl	$1, %edx
	vmovdqu32	(%rbx), %zmm2
	vmovdqu32	64(%rbx), %zmm3
	vmovdqu32	192(%rbx), %zmm6
	vmovdqu32	128(%rbx), %zmm5
	vpsrlq	$45, %zmm18, %zmm1
	vpsllq	$19, %zmm18, %zmm0
	vpxord	.LC0(%rip), %zmm18, %zmm18
	vpternlogd	$86, %zmm18, %zmm1, %zmm0
	vmovdqa64	%zmm0, %zmm18
	je	.L21
	movl	$64, %edi
	vmovd	%eax, %xmm16
	vpxord	%zmm0, %zmm2, %zmm2
	vpsllq	$17, %zmm0, %zmm19
	subl	%eax, %edi
	vpxord	%zmm19, %zmm3, %zmm3
	vpsrlq	$13, %zmm0, %zmm19
	vpxord	%zmm19, %zmm5, %zmm5
	vmovq	%rdi, %xmm4
	movl	$1, %edi
	vpbroadcastq	%rdi, %zmm1
	vpbroadcastq	%rdi, %zmm23
	vpsrlq	%xmm4, %zmm1, %zmm1
	vpsllq	%xmm16, %zmm23, %zmm17
	vpternlogd	$86, %zmm2, %zmm1, %zmm17
	vmovdqu64	304(%rsp), %zmm2
	vpsrlq	%xmm4, %zmm2, %zmm1
	vpsllq	%xmm16, %zmm2, %zmm2
	vpternlogd	$86, %zmm3, %zmm1, %zmm2
	vmovdqu64	368(%rsp), %zmm3
	vpsrlq	%xmm4, %zmm3, %zmm1
	vpsllq	%xmm16, %zmm3, %zmm3
	vpternlogd	$86, %zmm5, %zmm1, %zmm3
	vmovdqu64	432(%rsp), %zmm1
	vpsrlq	$33, %zmm0, %zmm5
	vpsllq	$31, %zmm0, %zmm0
	vpsrlq	%xmm4, %zmm1, %zmm4
	vpsllq	%xmm16, %zmm1, %zmm1
	vpord	%zmm4, %zmm1, %zmm1
	vpternlogd	$86, %zmm1, %zmm5, %zmm0
	vpxord	%zmm6, %zmm0, %zmm0
	cmpl	$8, %eax
	je	.L38
	movl	%eax, %edx
	jmp	.L24
.L38:
	movl	$8, %edx
	.p2align 4
	.p2align 3
.L23:
	vmovdqu64	%zmm17, (%rbx)
	movq	%rbx, %rcx
	vmovdqu64	%zmm2, 64(%rbx)
	vmovdqu64	%zmm3, 128(%rbx)
	vmovdqu64	%zmm0, 192(%rbx)
	vzeroupper
	call	a1_round
	movq	%rdx, %rax
	vmovdqu64	128(%rbx), %zmm3
	andl	$1, %eax
	vmovq	1264(%rsp,%rax,8), %xmm5
	vpinsrq	$1, 1280(%rsp,%rax,8), %xmm5, %xmm1
	vmovq	1232(%rsp,%rax,8), %xmm5
	vpinsrq	$1, 1248(%rsp,%rax,8), %xmm5, %xmm0
	vmovq	1168(%rsp,%rax,8), %xmm6
	vmovq	1200(%rsp,%rax,8), %xmm5
	vpinsrq	$1, 1216(%rsp,%rax,8), %xmm5, %xmm2
	vinserti64x2	$0x1, %xmm1, %ymm0, %ymm0
	vpinsrq	$1, 1184(%rsp,%rax,8), %xmm6, %xmm1
	movl	%edx, %eax
	notl	%eax
	andl	$1, %eax
	vmovq	1264(%rsp,%rax,8), %xmm5
	vmovq	1232(%rsp,%rax,8), %xmm6
	vinserti64x2	$0x1, %xmm2, %ymm1, %ymm1
	vpinsrq	$1, 1248(%rsp,%rax,8), %xmm6, %xmm2
	vmovq	1168(%rsp,%rax,8), %xmm6
	vinserti64x4	$0x1, %ymm0, %zmm1, %zmm1
	vpinsrq	$1, 1280(%rsp,%rax,8), %xmm5, %xmm0
	vmovq	1200(%rsp,%rax,8), %xmm5
	vpinsrq	$1, 1216(%rsp,%rax,8), %xmm5, %xmm4
	vpxord	(%rbx), %zmm1, %zmm17
	vinserti64x2	$0x1, %xmm0, %ymm2, %ymm2
	vpinsrq	$1, 1184(%rsp,%rax,8), %xmm6, %xmm0
	vinserti64x2	$0x1, %xmm4, %ymm0, %ymm0
	vinserti64x4	$0x1, %ymm2, %zmm0, %zmm0
	vpsrlq	$45, %zmm0, %zmm2
	vpsllq	$19, %zmm0, %zmm0
	vpternlogd	$86, 64(%rbx), %zmm0, %zmm2
	vpbroadcastq	%rdx, %zmm0
	incq	%rdx
	vpxord	%zmm0, %zmm2, %zmm2
	vpsrlq	$21, %zmm1, %zmm0
	vpsllq	$43, %zmm1, %zmm1
	vpternlogd	$86, 192(%rbx), %zmm1, %zmm0
	cmpq	$16, %rdx
	jne	.L23
	movl	$6, %edx
	.p2align 4
	.p2align 3
.L25:
	vmovdqu64	%zmm17, (%rbx)
	movq	%rbx, %rcx
	vmovdqu64	%zmm2, 64(%rbx)
	vmovdqu64	%zmm3, 128(%rbx)
	vmovdqu64	%zmm0, 192(%rbx)
	vzeroupper
	call	a1_round
	vmovdqu64	(%rbx), %zmm17
	vmovdqu64	64(%rbx), %zmm2
	vmovdqu64	128(%rbx), %zmm3
	vmovdqu64	192(%rbx), %zmm0
	decl	%edx
	jne	.L25
	vpxord	.LC21(%rip), %zmm3, %zmm4
	vpxord	.LC19(%rip), %zmm17, %zmm17
	movl	$1000000, %edx
	vpxord	.LC20(%rip), %zmm2, %zmm2
	vpxord	.LC22(%rip), %zmm0, %zmm3
	vpxor	%xmm5, %xmm5, %xmm5
	vmovdqu64	%zmm5, 48(%rsp)
	.p2align 4
	.p2align 3
.L26:
	vmovdqu64	%zmm17, (%rbx)
	movq	%rbx, %rcx
	vmovdqu64	%zmm2, 64(%rbx)
	vmovdqu64	%zmm4, 128(%rbx)
	vmovdqu64	%zmm3, 192(%rbx)
	vzeroupper
	call	a1_round
	vmovdqu64	(%rbx), %zmm17
	vmovdqu64	64(%rbx), %zmm2
	vmovdqu64	128(%rbx), %zmm4
	vmovdqu64	192(%rbx), %zmm3
	vpxord	48(%rsp), %zmm17, %zmm5
	vmovdqu32	%zmm5, 48(%rsp)
	decl	%edx
	jne	.L26
	vmovdqu64	%zmm4, 304(%rsp)
	vmovdqu64	%zmm3, 240(%rsp)
	vmovdqu64	%zmm2, 176(%rsp)
	vmovdqu64	%zmm17, 112(%rsp)
/APP
 # 146 "F:/lunwen/github_release/src/tempest_a1_avx512.c" 1
	rdtsc
 # 0 "" 2
/NO_APP
	salq	$32, %rdx
	movl	%eax, %eax
	movq	%rdx, %rdi
	orq	%rax, %rdi
	vzeroupper
	call	now_ms
	vmovdqu64	304(%rsp), %zmm4
	vmovdqu64	240(%rsp), %zmm3
	vmovapd	%xmm0, %xmm7
	movl	$20000000, %r10d
	vmovdqu64	176(%rsp), %zmm2
	vmovdqu64	112(%rsp), %zmm17
	.p2align 4
	.p2align 3
.L27:
	movq	%rbx, %rcx
	leaq	848(%rsp), %r9
	leaq	912(%rsp), %r8
	leaq	976(%rsp), %rdx
	vmovdqu64	%zmm17, (%rbx)
	vmovdqu64	%zmm2, 64(%rbx)
	vmovdqu64	%zmm4, 128(%rbx)
	vmovdqu64	%zmm3, 192(%rbx)
	vzeroupper
	call	a1_round
	vmovdqu64	64(%rbx), %zmm2
	vmovdqu64	128(%rbx), %zmm4
	leaq	1040(%rsp), %rcx
	vmovdqu64	192(%rbx), %zmm3
	vmovdqu64	(%rbx), %zmm17
	movq	%rsi, 32(%rsp)
	vmovdqu64	%zmm2, 976(%rsp)
	vmovdqu64	%zmm2, 240(%rsp)
	vmovdqu64	%zmm4, 912(%rsp)
	vmovdqu64	%zmm4, 176(%rsp)
	vmovdqu64	%zmm3, 848(%rsp)
	vmovdqu64	%zmm3, 112(%rsp)
	vmovdqu64	%zmm17, 784(%rsp)
	vzeroupper
	call	a1_output
	vmovdqu64	240(%rsp), %zmm2
	vmovdqu64	176(%rsp), %zmm4
	movq	%rsi, 32(%rsp)
	leaq	1040(%rsp), %rcx
	vmovdqu64	112(%rsp), %zmm3
	vmovdqu64	1040(%rsp), %zmm16
	vmovdqu64	%zmm17, 976(%rsp)
	vmovdqu64	%zmm2, 912(%rsp)
	vmovdqu64	%zmm4, 848(%rsp)
	vmovdqu64	%zmm3, 784(%rsp)
	vzeroupper
	call	a1_output
	vmovdqu32	48(%rsp), %zmm6
	decq	%r10
	vmovdqu64	112(%rsp), %zmm3
	vmovdqu64	176(%rsp), %zmm4
	vmovdqu64	240(%rsp), %zmm2
	vpternlogd	$150, 1040(%rsp), %zmm6, %zmm16
	vmovdqu64	%zmm16, 48(%rsp)
	jne	.L27
	vmovdqu32	%zmm16, 48(%rsp)
	vxorps	%xmm6, %xmm6, %xmm6
	vzeroupper
	call	now_ms
/APP
 # 146 "F:/lunwen/github_release/src/tempest_a1_avx512.c" 1
	rdtsc
 # 0 "" 2
/NO_APP
	vsubsd	%xmm7, %xmm0, %xmm0
	vdivsd	.LC8(%rip), %xmm0, %xmm2
	movl	%eax, %eax
	vmovsd	.LC26(%rip), %xmm3
	salq	$32, %rdx
	orq	%rax, %rdx
	vmovdqu32	48(%rsp), %zmm16
	leaq	.LC29(%rip), %rcx
	subq	%rdi, %rdx
	vcvtusi2sdq	%rdx, %xmm6, %xmm0
	vdivsd	%xmm2, %xmm0, %xmm1
	vmovsd	.LC27(%rip), %xmm0
	vdivsd	%xmm2, %xmm0, %xmm0
	vmovsd	.LC28(%rip), %xmm2
	vdivsd	%xmm3, %xmm1, %xmm1
	vdivsd	%xmm3, %xmm0, %xmm5
	vextracti64x4	$0x1, %zmm16, %ymm3
	vpaddq	%ymm16, %ymm3, %ymm3
	vextracti64x2	$0x1, %ymm3, %xmm0
	vpaddq	%xmm3, %xmm0, %xmm0
	vpshufd	$238, %xmm0, %xmm3
	vpaddq	%xmm3, %xmm0, %xmm0
	vmovq	1112(%rsp), %xmm3
	vdivsd	%xmm1, %xmm2, %xmm2
	vmovq	%xmm1, %rdx
	vpxorq	%xmm3, %xmm0, %xmm0
	vmovq	%xmm0, 1112(%rsp)
	vmovq	%xmm5, %r8
	vmulsd	%xmm2, %xmm5, %xmm5
	vmovq	%r8, %xmm2
	vmovq	%xmm5, %r9
	vmovapd	%xmm5, %xmm3
	vzeroupper
	call	__mingw_printf
	nop
	vmovups	1792(%rsp), %xmm6
	vmovups	1808(%rsp), %xmm7
	xorl	%eax, %eax
	addq	$1824, %rsp
	popq	%rbx
	popq	%rsi
	popq	%rdi
	popq	%rbp
	popq	%r12
	ret
	.p2align 4
	.p2align 3
.L21:
	vmovdqu32	.LC19(%rip), %zmm1
	vmovdqu32	.LC20(%rip), %zmm4
	movl	%eax, %edx
	vpternlogd	$150, %zmm0, %zmm1, %zmm2
	vpsllq	$17, %zmm0, %zmm1
	vpternlogd	$150, %zmm1, %zmm4, %zmm3
	vmovdqu32	.LC21(%rip), %zmm4
	vpsrlq	$13, %zmm0, %zmm1
	vmovdqa32	%zmm2, %zmm17
	vmovdqa32	%zmm3, %zmm2
	vpternlogd	$150, %zmm1, %zmm4, %zmm5
	vpxord	.LC22(%rip), %zmm6, %zmm1
	vpsrlq	$33, %zmm0, %zmm4
	vpsllq	$31, %zmm0, %zmm0
	vmovdqa32	%zmm5, %zmm3
	vpternlogd	$86, %zmm1, %zmm4, %zmm0
	jmp	.L24
	.seh_endproc
	.section .rdata,"dr"
	.align 64
.LC0:
	.long	2135587861
	.long	-1640531527
	.long	2135587861
	.long	-1640531527
	.long	2135587861
	.long	-1640531527
	.long	2135587861
	.long	-1640531527
	.long	2135587861
	.long	-1640531527
	.long	2135587861
	.long	-1640531527
	.long	2135587861
	.long	-1640531527
	.long	2135587861
	.long	-1640531527
	.align 8
.LC5:
	.quad	4354685564936845354
	.align 8
.LC6:
	.quad	6521908910823816487
	.align 8
.LC7:
	.quad	7987674495026412364
	.align 8
.LC8:
	.long	0
	.long	1083129856
	.align 64
.LC9:
	.quad	6072344679466677575
	.quad	6072344679466677575
	.quad	6072344679466677575
	.quad	6072344679466677575
	.quad	6072344679466677575
	.quad	6072344679466677575
	.quad	6072344679466677575
	.quad	6072344679466677575
	.align 64
.LC12:
	.quad	7640891576956012808
	.quad	7640891576956012808
	.quad	7640891576956012808
	.quad	7640891576956012808
	.quad	7640891576956012808
	.quad	7640891576956012808
	.quad	7640891576956012808
	.quad	7640891576956012808
	.align 64
.LC15:
	.quad	5
	.quad	6
	.quad	5
	.quad	6
	.quad	5
	.quad	6
	.quad	5
	.quad	6
	.align 64
.LC19:
	.long	1
	.long	0
	.long	1
	.long	0
	.long	1
	.long	0
	.long	1
	.long	0
	.long	1
	.long	0
	.long	1
	.long	0
	.long	1
	.long	0
	.long	1
	.long	0
	.align 64
.LC20:
	.long	2
	.long	0
	.long	2
	.long	0
	.long	2
	.long	0
	.long	2
	.long	0
	.long	2
	.long	0
	.long	2
	.long	0
	.long	2
	.long	0
	.long	2
	.long	0
	.align 64
.LC21:
	.long	3
	.long	0
	.long	3
	.long	0
	.long	3
	.long	0
	.long	3
	.long	0
	.long	3
	.long	0
	.long	3
	.long	0
	.long	3
	.long	0
	.long	3
	.long	0
	.align 64
.LC22:
	.long	4
	.long	0
	.long	4
	.long	0
	.long	4
	.long	0
	.long	4
	.long	0
	.long	4
	.long	0
	.long	4
	.long	0
	.long	4
	.long	0
	.long	4
	.long	0
	.align 32
.LC23:
	.quad	7763696387838107088
	.quad	-5109756097947997991
	.quad	-3499442433510419616
	.quad	-6540220794343932221
	.align 8
.LC26:
	.long	0
	.long	1104006501
	.align 8
.LC27:
	.long	0
	.long	1108546256
	.align 8
.LC28:
	.long	0
	.long	1075052544
	.def	__main;	.scl	2;	.type	32;	.endef
	.ident	"GCC: (Rev5, Built by MSYS2 project) 16.1.0"
