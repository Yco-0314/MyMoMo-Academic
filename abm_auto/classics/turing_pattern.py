"""Turing diffusion-driven instability (Gierer-Meinhardt) — a faithful grid-PDE reproduction.

Source: Turing, A. M. (1952) "The chemical basis of morphogenesis", Phil. Trans. R. Soc.
London B 237(641):37-72. doi:10.1098/rstb.1952.0012. Activator-inhibitor kinetics:
Gierer, A. & Meinhardt, H. (1972) "A theory of biological pattern formation",
Kybernetik 12(1):30-39. doi:10.1007/BF00289234.

IMPORTANT (honesty, binds the FINDINGS): this is a two-species reaction-diffusion
PARTIAL-DIFFERENTIAL-EQUATION integrated on a grid — a CELLULAR / grid-PDE model, NOT an
agent-stepping ABM. There are no agents that perceive, decide and act; no scheduler over
an agent roster; no per-agent step. It is a single synchronous update (explicit forward
Euler with a 5-point periodic Laplacian) applied to every grid cell of the two
concentration fields at once. We disclose this exactly as the gray_scott / game_of_life /
forest_fire reproductions disclose they are cellular / grid-PDE models. The lock-first +
honest-verdict + L3-bundle discipline still applies in full.

The model (Turing 1952 morphogenesis via the Gierer-Meinhardt 1972 activator-inhibitor
kinetics):

    da/dt = rho * (a^2 / h - a) + Du * lap(a)          (activator, short-range)
    dh/dt = rho * (a^2     - h) + Dv * lap(h)          (inhibitor, long-range)

on an L x L PERIODIC (toroidal) grid. ``a`` is the ACTIVATOR: it self-enhances (the
autocatalytic a^2/h term) but is antagonised by the inhibitor ``h``, which ``a`` itself
produces (the a^2 source in the h equation). The kinetics have a single non-trivial
homogeneous steady state a* = h* = 1. ``lap`` is the 5-point Laplacian with wrap-around
(periodic) boundaries.

The diffusion-DRIVEN instability (Turing's central result). Linearise the kinetics about
(a*, h*) = (1, 1). The reaction Jacobian is

    J = rho * [[ 2a/h - 1 ,  -a^2/h^2 ],      =  rho * [[  1 , -1 ],
               [   2a      ,     -1    ]]                [  2 , -1 ]]   at (1, 1).

WITHOUT diffusion the homogeneous state does not grow (trace J = 0, det J = rho^2 > 0: a
neutral centre — a is neither amplified nor damped by the reaction alone; the nonlinear
saturation a^2/h then holds it exactly flat, which the simulation confirms: with the
diffusion ratio d = Dv/Du = 1 the field stays homogeneous). WITH unequal diffusion the
long-range inhibitor (Dv > Du) can outrun and quench the activator locally while letting it
grow elsewhere: for a spatial wavenumber q (angular, rad per unit length) the growth rate
is the larger eigenvalue of  J - q^2 * diag(Du, Dv), whose sign is set by

    D(q^2) = (Jaa - Du q^2)(Jhh - Dv q^2) - Jah*Jha
           = Du*Dv*q^4 - (Du*Jhh + Dv*Jaa) q^2 + det(J).

D(q^2) < 0 for a finite band of q (the UNSTABLE band k1 < q < k2) once the diffusion ratio
exceeds the critical ratio d_c; the FASTEST-GROWING mode q* = argmax_q growth is the
wavelength that first appears. For this Jacobian d_c = 3 + 2*sqrt(2) ~= 5.828 (the classic
Gierer-Meinhardt value). We drive the Turing arm at d = 1.5 * d_c, comfortably inside the
regime, and compare the emergent dominant wavenumber against q* derived from THIS linear
analysis (not fitted).

Numerics (FIXED, locked before running; not tuned):
  * 128 x 128 grid, unit spacing dx = 1.0 (the wavenumbers below are per grid unit).
  * rho = 1.0 (reaction rate).
  * Du = 0.5; Dv = 1.5 * d_c * Du (the Turing arm). The CONTROL sets Dv = Du (d = 1).
  * Explicit forward Euler in time with step dt = 0.005. The diffusive stability limit of
    the 5-point Laplacian is dt < dx^2 / (4 * max(Du, Dv)); with Dv ~ 4.37 that limit is
    ~ 0.057, so dt = 0.005 is comfortably stable, and the reaction terms are O(rho) = O(1)
    with the saturating a^2/h kinetics, far below any reaction-stiffness limit at dt=0.005.
  * Initial condition: a = h = 1 (the homogeneous steady state) plus small seeded Gaussian
    noise (amplitude 0.01) — the standard "small random perturbation of the uniform state"
    that the unstable band then selectively amplifies. The noise is the only randomness and
    is deterministic given ``seed``. ``a`` and ``h`` are floored at a small positive value
    each step to keep the a^2/h kinetics well defined (h never reaches 0).

Metrics (the locked grading quantities; all deterministic given seed):
  * ``spatial_cov(a)``: spatial coefficient of variation std(a)/mean(a) of the activator
    field — ~0 in the homogeneous regime (control), >> 0.05 once a finite-amplitude pattern
    forms (P1).
  * ``dominant_wavenumber(a)``: the peak of the radially-averaged 2D power spectrum of the
    (mean-subtracted) activator field, returned as an ANGULAR wavenumber k = 2*pi*m/(N*dx)
    to match the dispersion-relation q* (P2).
  * amplitude series std(a) over the run: P3 checks the last ~20% is flat (a stationary,
    non-oscillatory Turing pattern, not a travelling/oscillating wave).

``dispersion_qstar`` / ``unstable_band`` / ``critical_ratio`` implement the linear analysis
above in closed / scanned form (no fitting). NumPy holds the two fields and does the
vectorised Laplacian (np.roll) + reaction; the result is the bit-for-bit deterministic
Gierer-Meinhardt orbit for a given (Du, Dv, seed).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Fixed reaction / numerical constants (locked; PREDICTIONS-locked.md).
RHO = 1.0            # reaction rate
DU = 0.5             # activator diffusion (short range)
GRID_N = 128         # cells per side
DX = 1.0             # grid spacing (unit)
DT = 0.005           # explicit-Euler time step
NOISE = 0.01         # amplitude of the seeded IC perturbation about (a*, h*) = (1, 1)

# Reaction-Jacobian entries at the homogeneous steady state (a*, h*) = (1, 1), in units of
# rho. da/dt = rho(a^2/h - a): d/da = 2a/h - 1 = 1, d/dh = -a^2/h^2 = -1.
# dh/dt = rho(a^2 - h):       d/da = 2a       = 2, d/dh = -1.
_JAA, _JAH, _JHA, _JHH = 1.0, -1.0, 2.0, -1.0   # (times rho)

# Classic Gierer-Meinhardt critical diffusion ratio d_c = Dv/Du at the Turing threshold for
# this Jacobian: solving (Dv*Jaa + Du*Jhh)^2 = 4*Du*Dv*det(J) with Du=1 gives Dv=3+2*sqrt(2).
D_C = 3.0 + 2.0 * math.sqrt(2.0)   # ~= 5.828427


# -- the 5-point periodic Laplacian ------------------------------------------------

def laplacian(field: np.ndarray, dx: float) -> np.ndarray:
    """5-point discrete Laplacian of ``field`` on a PERIODIC (toroidal) grid.

    lap(f)_{ij} = (f_{i+1,j} + f_{i-1,j} + f_{i,j+1} + f_{i,j-1} - 4 f_{ij}) / dx^2.
    Implemented with np.roll (which wraps the edges, giving the periodic stencil exactly).
    """
    return (
        np.roll(field, 1, axis=0)
        + np.roll(field, -1, axis=0)
        + np.roll(field, 1, axis=1)
        + np.roll(field, -1, axis=1)
        - 4.0 * field
    ) / (dx * dx)


# -- linear dispersion analysis (the P2 reference; derived, not fitted) ------------

def critical_ratio() -> float:
    """The critical diffusion ratio d_c = Dv/Du above which the homogeneous Gierer-Meinhardt
    steady state (a*=h*=1) goes Turing-unstable. Closed form 3 + 2*sqrt(2) for this
    Jacobian (independent of rho and Du: only the RATIO Dv/Du matters at threshold)."""
    return D_C


def _dispersion_D(q2: np.ndarray | float, rho: float, Du: float, Dv: float):
    """D(q^2) = det(J - q^2 diag(Du, Dv)) (rho-scaled Jacobian). The larger eigenvalue of
    (J - q^2 diag) has POSITIVE real part iff D(q^2) < 0 (the trace is <= 0 for q^2 >= 0
    here, so an unstable eigenvalue requires a negative determinant). Vectorises over q2."""
    Jaa, Jah, Jha, Jhh = rho * _JAA, rho * _JAH, rho * _JHA, rho * _JHH
    det_J = Jaa * Jhh - Jah * Jha
    return Du * Dv * q2 * q2 - (Du * Jhh + Dv * Jaa) * q2 + det_J


def _growth_rate(q2: np.ndarray, rho: float, Du: float, Dv: float) -> np.ndarray:
    """Real part of the larger eigenvalue of J - q^2 diag(Du, Dv), vectorised over q2 (the
    linear growth rate of a perturbation with angular wavenumber q = sqrt(q2))."""
    Jaa, Jah, Jha, Jhh = rho * _JAA, rho * _JAH, rho * _JHA, rho * _JHH
    T = (Jaa + Jhh) - (Du + Dv) * q2                 # trace(J - q^2 diag)
    D = _dispersion_D(q2, rho, Du, Dv)               # det(J - q^2 diag)
    disc = T * T - 4.0 * D
    # real eigenvalue pair when disc>=0 (larger root); complex pair -> real part T/2.
    return np.where(disc >= 0.0, 0.5 * (T + np.sqrt(np.abs(disc))), 0.5 * T)


def dispersion_qstar(rho: float = RHO, Du: float = DU, Dv: float = DU,
                     *, q_max: Optional[float] = None,
                     n_scan: int = 400001) -> float:
    """The fastest-growing angular wavenumber q* = argmax_q growth_rate(q), from the linear
    dispersion relation of the Gierer-Meinhardt kinetics with diffusions (Du, Dv). Scans q on
    a fine grid up to ``q_max`` (default: a few /min-diffusion length, well past the band).
    Returns 0.0 if no mode has positive growth (no Turing instability)."""
    if q_max is None:
        q_max = math.sqrt(5.0 / min(Du, Dv))
    q2 = np.linspace(1e-9, q_max * q_max, n_scan)
    growth = _growth_rate(q2, rho, Du, Dv)
    i = int(np.argmax(growth))
    if growth[i] <= 0.0:
        return 0.0
    return float(math.sqrt(q2[i]))


def unstable_band(rho: float = RHO, Du: float = DU, Dv: float = DU,
                  *, q_max: Optional[float] = None,
                  n_scan: int = 400001) -> Optional[Tuple[float, float]]:
    """The Turing UNSTABLE band (k1, k2) of angular wavenumbers where the growth rate is
    positive (equivalently D(q^2) < 0). Returns None if the band is empty (no instability)."""
    if q_max is None:
        q_max = math.sqrt(5.0 / min(Du, Dv))
    q2 = np.linspace(1e-9, q_max * q_max, n_scan)
    D = _dispersion_D(q2, rho, Du, Dv)
    unstable = q2[D < 0.0]
    if unstable.size == 0:
        return None
    return float(math.sqrt(unstable.min())), float(math.sqrt(unstable.max()))


# -- radially-averaged power spectrum -> dominant wavenumber -----------------------

def dominant_wavenumber(field: np.ndarray, dx: float = DX) -> Dict[str, Any]:
    """Dominant (angular) wavenumber of a 2D field from its radially-averaged power spectrum.

    Mean-subtract, take |FFT2|^2, bin by integer radial mode number m = round(|k_cycles| *
    N * dx) (so mode m corresponds to k_cycles = m/(N*dx) cycles per unit length), and pick
    the peak mode (DC excluded). Returns the peak mode index and the angular wavenumber
    k = 2*pi * m / (N*dx) (rad per unit length), which is directly comparable to the
    dispersion-relation q* (both are angular). Also returns the radial spectrum for
    inspection."""
    f = np.asarray(field, dtype=np.float64)
    n = f.shape[0]
    fc = f - f.mean()
    power = np.abs(np.fft.fft2(fc)) ** 2
    kx = np.fft.fftfreq(n, d=dx)                     # cycles per unit length
    KX, KY = np.meshgrid(kx, kx, indexing="ij")
    kmag_cycles = np.sqrt(KX * KX + KY * KY)
    mode = np.rint(kmag_cycles * n * dx).astype(int)  # integer radial mode number
    max_m = n // 2
    radial = np.zeros(max_m + 1, dtype=np.float64)
    for m in range(max_m + 1):
        sel = mode == m
        if sel.any():
            radial[m] = float(power[sel].mean())
    radial[0] = 0.0                                   # exclude the DC (mean) component
    m_peak = int(np.argmax(radial))
    k_cycles = m_peak / (n * dx)
    k_angular = 2.0 * math.pi * k_cycles
    return {
        "mode_peak": m_peak,
        "k_cycles": k_cycles,
        "k_angular": k_angular,
        "radial_power": radial.tolist(),
    }


# -- Model ------------------------------------------------------------------------

class TuringModel:
    """Gierer-Meinhardt activator-inhibitor reaction-diffusion (Turing 1952 morphogenesis)
    on an L x L periodic grid.

    Construct with the two diffusion constants (Du, Dv), the reaction rate rho, the grid
    size, spacing, time step, IC noise amplitude, and a seed. ``step`` performs one explicit
    forward-Euler update of both fields; ``run`` integrates a fixed number of steps and
    records the activator amplitude (spatial std) + CoV at regular intervals. Deterministic
    given ``seed``.

    This is a grid PDE (disclosed), not an agent model, so there is no AgentSet / scheduler;
    the "tick" is the synchronous field update. Set Dv = Du (d = 1) for the diffusion-off /
    equal-diffusion CONTROL, which stays homogeneous.
    """

    def __init__(self, *, Du: float = DU, Dv: float = DU, rho: float = RHO,
                 n: int = GRID_N, dx: float = DX, dt: float = DT,
                 noise: float = NOISE, seed: int = 0) -> None:
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if dx <= 0:
            raise ValueError(f"need dx > 0 (got {dx})")
        if Du <= 0 or Dv <= 0:
            raise ValueError(f"need Du>0, Dv>0 (got Du={Du}, Dv={Dv})")
        if rho <= 0:
            raise ValueError(f"need rho > 0 (got {rho})")
        if dt <= 0:
            raise ValueError(f"need dt > 0 (got {dt})")
        if noise < 0:
            raise ValueError(f"need noise >= 0 (got {noise})")
        self.Du = float(Du)
        self.Dv = float(Dv)
        self.rho = float(rho)
        self.n = int(n)
        self.dx = float(dx)
        self.dt = float(dt)
        self.noise = float(noise)
        self.seed = int(seed)
        self.t = 0

        # Stability guard: explicit-Euler diffusion needs dt < dx^2 / (4*max(Du,Dv)).
        self.diffusion_dt_limit = self.dx * self.dx / (4.0 * max(self.Du, self.Dv))
        if self.dt >= self.diffusion_dt_limit:
            raise ValueError(
                f"dt={self.dt} violates the diffusion stability limit "
                f"dx^2/(4*max(Du,Dv))={self.diffusion_dt_limit:.4g}")

        self._rng = np.random.default_rng(seed)
        self.a, self.h = self._initial_condition()

    @property
    def diffusion_ratio(self) -> float:
        """d = Dv / Du (the Turing control knob)."""
        return self.Dv / self.Du

    def _initial_condition(self) -> Tuple[np.ndarray, np.ndarray]:
        """Homogeneous steady state a = h = 1 plus small seeded Gaussian noise (the standard
        'small random perturbation of the uniform state'). Deterministic given ``seed``."""
        a = 1.0 + self.noise * self._rng.standard_normal((self.n, self.n))
        h = 1.0 + self.noise * self._rng.standard_normal((self.n, self.n))
        np.clip(a, 1e-6, None, out=a)
        np.clip(h, 1e-6, None, out=h)
        return a, h

    # -- one synchronous explicit-Euler update of both fields --
    def step(self) -> None:
        """Advance both fields one time step (forward Euler).

        Uses one shared start-of-step snapshot for the Laplacians and the reaction, so the
        update is synchronous (both fields advance together off the same current state). The
        fields are floored at a small positive value to keep the a^2/h kinetics well defined
        (h never reaches 0)."""
        a, h = self.a, self.h
        la = laplacian(a, self.dx)
        lh = laplacian(h, self.dx)
        aa = a * a
        da = self.rho * (aa / h - a) + self.Du * la
        dh = self.rho * (aa - h) + self.Dv * lh
        a_new = a + self.dt * da
        h_new = h + self.dt * dh
        np.clip(a_new, 1e-6, None, out=a_new)
        np.clip(h_new, 1e-6, None, out=h_new)
        self.a, self.h = a_new, h_new
        self.t += 1

    # -- metrics --
    def spatial_cov(self) -> float:
        """Spatial coefficient of variation std(a)/mean(a) of the ACTIVATOR field. ~0 for a
        homogeneous field (control); >> 0.05 once a finite-amplitude pattern has formed."""
        m = float(self.a.mean())
        s = float(self.a.std())
        return s / abs(m) if m != 0.0 else s

    def amplitude(self) -> float:
        """Pattern amplitude = spatial standard deviation of the activator field."""
        return float(self.a.std())

    def dominant_wavenumber(self) -> Dict[str, Any]:
        """The emergent dominant (angular) wavenumber from the activator field's
        radially-averaged power spectrum (see the module-level function)."""
        return dominant_wavenumber(self.a, self.dx)

    # -- run --
    def run(self, n_steps: int = 30000, *, record_every: int = 1000) -> Dict[str, Any]:
        """Integrate ``n_steps`` explicit-Euler steps, recording the activator amplitude
        (spatial std) and CoV every ``record_every`` steps (and at t=0 and the final step).

        Returns the final field metrics, the measured dominant wavenumber, the linear-theory
        q* + unstable band for these (rho, Du, Dv), and the recorded series (for the P3
        stationarity check). Deterministic given the construction seed."""
        if n_steps < 0:
            raise ValueError(f"need n_steps >= 0 (got {n_steps})")
        if record_every <= 0:
            raise ValueError(f"need record_every > 0 (got {record_every})")
        step_series: List[int] = []
        amp_series: List[float] = []
        cov_series: List[float] = []

        def record() -> None:
            step_series.append(self.t)
            amp_series.append(self.amplitude())
            cov_series.append(self.spatial_cov())

        record()  # t=0 baseline
        for i in range(n_steps):
            self.step()
            if (i + 1) % record_every == 0 or (i + 1) == n_steps:
                record()

        wn = self.dominant_wavenumber()
        qstar = dispersion_qstar(self.rho, self.Du, self.Dv)
        band = unstable_band(self.rho, self.Du, self.Dv)
        return {
            "Du": self.Du, "Dv": self.Dv, "rho": self.rho,
            "diffusion_ratio": self.diffusion_ratio,
            "n": self.n, "dx": self.dx, "dt": self.dt,
            "noise": self.noise, "seed": self.seed,
            "n_steps": n_steps, "record_every": record_every,
            "final_cov": self.spatial_cov(),
            "final_amplitude": self.amplitude(),
            "final_mean_a": float(self.a.mean()),
            "final_mean_h": float(self.h.mean()),
            "k_meas_angular": wn["k_angular"],
            "k_meas_mode": wn["mode_peak"],
            "k_meas_cycles": wn["k_cycles"],
            "qstar": qstar,
            "unstable_band": list(band) if band is not None else None,
            "critical_ratio": critical_ratio(),
            "step_series": step_series,
            "amplitude_series": amp_series,
            "cov_series": cov_series,
            "radial_power": wn["radial_power"],
        }


# -- run helpers ------------------------------------------------------------------

def run_regime(*, Du: float = DU, Dv: float = DU, rho: float = RHO, n: int = GRID_N,
               dx: float = DX, dt: float = DT, noise: float = NOISE, seed: int = 0,
               n_steps: int = 30000, record_every: int = 1000) -> Dict[str, Any]:
    """Integrate one Gierer-Meinhardt regime at a given (Du, Dv) and the fixed numerics;
    return the run summary (final metrics + measured wavenumber + linear-theory q*/band +
    series). Deterministic given ``seed``."""
    return TuringModel(Du=Du, Dv=Dv, rho=rho, n=n, dx=dx, dt=dt, noise=noise,
                       seed=seed).run(n_steps, record_every=record_every)


def amplitude_is_stationary(step_series, amplitude_series, *, tail_frac: float = 0.2,
                            max_rel_change_per_1e3: float = 0.05) -> Dict[str, Any]:
    """P3 test: over the last ``tail_frac`` of the run, is the pattern amplitude FLAT?

    Looks at the trailing ``tail_frac`` fraction of the recorded amplitude series and, for
    each consecutive pair, computes the relative change normalised to 1000 steps:
        |amp[i+1] - amp[i]| / amp[i] * (1000 / delta_steps).
    Returns whether the max such normalised change is below ``max_rel_change_per_1e3`` (a
    flat, non-oscillatory, stationary pattern), plus the measured max change. A field that
    stays exactly homogeneous (amplitude ~ 0) is treated as trivially stationary only if it
    genuinely does not move (guarded against 0/0)."""
    steps = list(step_series)
    amps = list(amplitude_series)
    if len(amps) < 2:
        return {"stationary": True, "max_rel_change_per_1e3": 0.0, "tail_amplitudes": amps}
    start = int((1.0 - tail_frac) * len(amps))
    start = min(start, len(amps) - 2)               # keep at least one pair
    tail_amps = amps[start:]
    tail_steps = steps[start:]
    max_change = 0.0
    for i in range(len(tail_amps) - 1):
        a0, a1 = tail_amps[i], tail_amps[i + 1]
        dstep = tail_steps[i + 1] - tail_steps[i]
        if dstep <= 0:
            continue
        base = abs(a0)
        if base < 1e-12:
            change = 0.0 if abs(a1) < 1e-12 else float("inf")
        else:
            change = abs(a1 - a0) / base * (1000.0 / dstep)
        if change > max_change:
            max_change = change
    return {
        "stationary": max_change < max_rel_change_per_1e3,
        "max_rel_change_per_1e3": max_change,
        "tail_amplitudes": tail_amps,
        "tail_steps": tail_steps,
    }
