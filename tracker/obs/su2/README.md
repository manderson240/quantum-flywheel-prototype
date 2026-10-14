README.txt

Quantum Advantage Tracker submission draft
Instance: su2_lsh_hadron_dynamics_N60_x100_dt0p0015_t20

This submission reports the x=100, 20-Trotter-step instance of the 60-site SU(2)
lattice gauge theory dynamics experiment in the LSH encoding. The hardware
implementation uses 120 qubits (2 qubits per site), expectation-value estimation
from qubit Z-measurements, and readout-error mitigation. The classical benchmark
suite for this instance is Tensor Network (TN), Pauli Propagation on CPU
(PP_CPU), and Pauli Propagation on GPU (PP_GPU).

SYSTEM AND IMPLEMENTATION

The target problem is real-time non-equilibrium dynamics of a staggered SU(2)
lattice gauge theory in the weak-coupling regime.

Parameters for this reported instance:

- lattice size N = 60
- coupling x = 100
- qubit count = 120
- Trotter step size dt = 0.0015
- number of Trotter steps = 20
- shot budget = 10,000 shots per Trotter step

For 20 Trotter steps, the two-qubit depth reaches 259.

Benchmark runtime table for step 20:

- QPU = 20 s
- TN = 2484.3693 s
- PP_CPU = 2930.4400 s
- PP_GPU = 8949.110 s

OBSERVABLE AND UNCERTAINTY STRATEGY

The reported measured observable here is the average fermion density n_f(t),
evaluated at Trotter step t = 20.

Since the exact many-body dynamics at this scale are not known, the primary
uncertainty proxy is taken from the exactly conserved global charge Q, whose
physical value is fixed to Q = 60.

Two distinct diagnostics are reported:

1. Primary uncertainty proxy:
   charge-conservation deviation, using the supplied stepwise Q-based error bar.

2. Secondary benchmark-consistency diagnostic:
   cross-method dispersion of n_f(t), quantified by the stepwise standard
   deviation across {TN, PP_CPU, PP_GPU, QPU}.

The second quantity should not be interpreted as a statistical confidence
interval; it is a method-to-method spread diagnostic.

PRIMARY CHARGE-CONSERVATION BENCHMARK AT STEP 20

At Trotter step 20, the conserved-charge values are:

Step TN PP_CPU PP_GPU QPU supplied_error_bar
20 60.00000000 60.00538161 59.99313828 59.99402699 0.005710650099

Using the exact conserved value Q = 60, the QPU charge deviation is:

|Q_QPU(20) - 60| = |59.99402699 - 60| = 0.00597301

The reported charge benchmark ise written as:

Q_QPU(20) = 59.99402699 +/- 0.005710650099

This corresponds to the interval:

[59.988316339901, 59.999737640099]

Across steps 1-20, the supplied charge-based error bar ranges from:

- minimum = 0.005710650099
- maximum = 0.04740887609

REPORTED OBSERVABLE AT STEP 20

The tracker-facing scalar observable for this instance is:

n_f(20) = -0.07723426024

Benchmark values at step 20 are:

Step TN PP_CPU PP_GPU QPU Median St.dev
20 0.2778348725 0.4081775866 0.2456276125 -0.07723426024 0.2617312425 0.2062335981

Signed deviations of QPU from the classical references:

- QPU - TN = -0.35506913274
- QPU - PP_CPU = -0.48541184684
- QPU - PP_GPU = -0.32286187274

Signed deviation of QPU from the stepwise median:

- QPU - Median = -0.33896550274

FULL 20-STEP OBSERVABLE BENCHMARK FOR n_f(t)

For x = 100, the full benchmark data are:

Step TN PP_CPU PP_GPU QPU Median St.dev
1 1.824222901 1.825335615 1.825336 1.77264257 1.824779258 0.02616639397
2 1.343818565 1.34880517 1.347871 1.234719061 1.345844782 0.05609802779
3 0.6852977079 0.698419082 0.693895 0.7005505103 0.696157041 0.006757945893
4 0.01781852652 0.04434743353 0.0317106 0.1125808617 0.03802901676 0.04206360493
5 -0.4957689977 -0.4510787869 -0.47774275 -0.3550984939 -0.4644107685 0.0626332901
6 -0.7447406887 -0.6794112084 -0.725069325 -0.4792900767 -0.7022402667 0.1216756278
7 -0.6994223897 -0.6144203611 -0.68012595 -0.405844541 -0.6472731556 0.1344237824
8 -0.4149706965 -0.3149685829 -0.3959514 -0.3160420563 -0.3559967282 0.05251500138
9 -0.009710517986 0.09777330494 0.010149475 -0.01701975315 0.0002194785072 0.05291043151
10 0.3744026048 0.4805343441 0.394226 0.1431540203 0.3843143024 0.1441771402
11 0.6163184396 0.7136997525 0.6325666 0.3540697043 0.6244425198 0.1559910262
12 0.6514199805 0.7369940536 0.6619868 0.4092782333 0.6567033902 0.142288607
13 0.4873750145 0.5641770138 0.4951614125 0.2630479833 0.4912682135 0.1308944493
14 0.1962856389 0.2712616284 0.2069994 0.1957298805 0.2016425194 0.0361687867
15 -0.1131674269 -0.03107728475 -0.096355725 0.00494274374 -0.06371650487 0.05537112224
16 -0.3336240614 -0.2318235614 -0.314319025 -0.08874021367 -0.2730712932 0.1113808299
17 -0.3941897866 -0.2691116404 -0.3787042075 -0.1962503187 -0.323907924 0.09384077972
18 -0.2807460955 -0.1325140013 -0.272586375 -0.1673053457 -0.2199458603 0.07462290823
19 -0.03330018147 0.1236920782 -0.035842523 -0.1490836294 -0.03457135223 0.1120789393
20 0.2778348725 0.4081775866 0.2456276125 -0.07723426024 0.2617312425 0.2062335981

COMPACT SUMMARY OVER STEPS 1-20

From the table above:

- Mean cross-method standard deviation = 0.09091461463315
- Maximum cross-method standard deviation = 0.2062335981 at step 20
- Mean absolute deviation of QPU from the stepwise median = 0.13764750287736

We report the x=100, t=20 instance of the 60-site SU(2) LSH dynamics
experiment. The measured scalar observable is n_f(20) = -0.07723426024.
Because exact dynamics are not available at this scale, the primary uncertainty
proxy is taken from the exactly conserved global charge Q = 60, for which the
QPU value at step 20 is 59.99402699 +/- 0.005710650099. Benchmark values for
n_f(20) are TN = 0.2778348725, PP_CPU = 0.4081775866, and
PP_GPU = 0.2456276125. The cross-method dispersion at step 20 is 0.2062335981,
reported as a benchmark-consistency diagnostic rather than a statistical
confidence interval.

FINAL CONSISTENCY NOTE

The step-20 charge "error bar" 0.005710650099 is close to, but not
identical with, the raw absolute deviation |59.99402699 - 60| = 0.00597301.
