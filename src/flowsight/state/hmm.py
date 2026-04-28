"""HMM-based state estimation per node.

Maps Hawkes intensity values into discrete latent states
{Normal, Stressed, Critical}. We fit a Gaussian HMM on the flattened
[T*N, 1] intensity matrix, then relabel components by ascending mean
so component-0 is always 'Normal'. Falls back to thresholding when
hmmlearn is unavailable.

Reference:
    Rabiner, L.R. (1989). "A tutorial on hidden Markov models and
    selected applications in speech recognition." Proc. IEEE.
"""

from __future__ import annotations

from typing import List, Sequence

import numpy as np

try:
    from hmmlearn.hmm import GaussianHMM
    _HAVE_HMMLEARN = True
except Exception:
    _HAVE_HMMLEARN = False


STATE_NAMES = ("Normal", "Stressed", "Critical")


class StateEstimator:
    def __init__(
        self,
        n_states: int = 3,
        n_iter: int = 50,
        random_state: int = 42,
    ) -> None:
        self.n_states = n_states
        self.n_iter = n_iter
        self.random_state = random_state
        self._model = None
        self._rank: dict | None = None

    def fit(self, intensity_traj: np.ndarray) -> "StateEstimator":
        if not _HAVE_HMMLEARN:
            return self
        flat = intensity_traj.reshape(-1, 1)
        if np.var(flat) < 1e-9:
            # Degenerate: nothing to learn, fall back to threshold.
            self._model = None
            return self
        model = GaussianHMM(
            n_components=self.n_states,
            covariance_type="full",
            n_iter=self.n_iter,
            random_state=self.random_state,
        )
        try:
            model.fit(flat)
        except Exception:
            self._model = None
            return self
        means = model.means_.ravel()
        order = list(np.argsort(means))
        self._rank = {raw: rank for rank, raw in enumerate(order)}
        self._model = model
        return self

    def predict(self, intensity_vec: Sequence[float]) -> List[str]:
        arr = np.asarray(intensity_vec, dtype=np.float64).reshape(-1, 1)
        if self._model is None or self._rank is None:
            return [self._threshold(v) for v in arr.ravel()]
        raw = self._model.predict(arr)
        n = len(STATE_NAMES)
        return [STATE_NAMES[min(self._rank.get(int(s), 0), n - 1)] for s in raw]

    @staticmethod
    def _threshold(v: float) -> str:
        if v < 0.3:
            return "Normal"
        if v < 1.0:
            return "Stressed"
        return "Critical"

    @staticmethod
    def state_to_multiplier(state: str) -> float:
        return {"Normal": 1.0, "Stressed": 1.4, "Critical": 2.5}.get(state, 1.0)
