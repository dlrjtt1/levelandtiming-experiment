"""Cumulative link mixed model (logit link, random intercept per listener) for ordinal 1-5 answers.

    P(y <= k | listener j) = logistic(theta_k - x'beta - u_j),   u_j ~ N(0, sigma^2)

Fitted by maximum likelihood; the random intercept is integrated out with (non-adaptive) Gauss-Hermite quadrature, 100 nodes;
the gradient is analytic, the optimiser is L-BFGS-B. Same model as R ordinal::clmm(y ~ x + (1|pid)), which uses adaptive
quadrature (nAGQ = 25); checked against it with analysis/check_clmm.py (log-likelihood, listener SD, likelihood ratio).

Used in run_analysis.py as a sensitivity analysis for the linear mixed model: does the conclusion change when the answers
are treated as ordered categories instead of numbers?
"""
import numpy as np
from scipy import optimize, special

NODES = 100   # non-adaptive: 25 nodes were too few with ~60 answers per listener (log-likelihood off by ~0.9 vs R)


def _expit(x):
    return special.expit(x)


class CLMM:
    def __init__(self, y, X, groups, nodes=NODES):
        y = np.asarray(y)
        cats = np.unique(y)                     # categories nobody used are left out (their threshold is not identified)
        self.cats = cats
        self.y = np.searchsorted(cats, y)       # 0 .. K-1
        self.K = len(cats)
        self.X = np.asarray(X, float)
        g, self.gidx = np.unique(np.asarray(groups), return_inverse=True)
        self.G = len(g)
        z, w = np.polynomial.hermite.hermgauss(nodes)
        self.z = np.sqrt(2.0) * z               # standard-normal nodes
        self.logw = np.log(w / np.sqrt(np.pi))
        self.p = self.X.shape[1]

    # parameters: [c_1 .. c_{K-1} (theta_1, then log increments), beta (p), log sigma]
    def _theta(self, c):
        th = np.empty(len(c)); th[0] = c[0]
        if len(c) > 1:
            th[1:] = c[0] + np.cumsum(np.exp(c[1:]))
        return th

    def negloglik(self, par, grad=True):
        K, p = self.K, self.p
        c, beta, ls = par[:K - 1], par[K - 1:K - 1 + p], par[-1]
        sig = np.exp(ls); th = self._theta(c)
        thx = np.concatenate([[-np.inf], th, [np.inf]])
        u = sig * self.z                                            # Q nodes
        eta = (self.X @ beta)[:, None] + u[None, :]                 # N x Q
        a = thx[self.y + 1][:, None] - eta; b = thx[self.y][:, None] - eta
        Fa, Fb = _expit(a), _expit(b)
        pr = np.clip(Fa - Fb, 1e-300, None)
        lp = np.log(pr)                                             # N x Q
        S = np.zeros((self.G, len(u)))
        np.add.at(S, self.gidx, lp)
        S += self.logw[None, :]
        ll_g = special.logsumexp(S, axis=1)
        nll = -ll_g.sum()
        if not grad:
            return nll
        r = np.exp(S - ll_g[:, None])[self.gidx]                    # posterior node weights, per observation (N x Q)
        fa = np.where(np.isfinite(a), Fa * (1 - Fa), 0.0); fb = np.where(np.isfinite(b), Fb * (1 - Fb), 0.0)
        d_eta = -(fa - fb) / pr                                     # d log p / d eta
        g_eta = (r * d_eta).sum(1)
        g_beta = self.X.T @ g_eta
        g_ls = (r * d_eta * u[None, :]).sum()
        # thresholds: d log p / d theta_y = fa / pr (upper), d log p / d theta_{y-1} = -fb / pr (lower)
        g_th = np.zeros(K - 1)
        up = (r * fa / pr).sum(1); lo = (r * fb / pr).sum(1)
        np.add.at(g_th, np.minimum(self.y, K - 2)[self.y <= K - 2], up[self.y <= K - 2])
        np.add.at(g_th, (self.y - 1)[self.y >= 1], -lo[self.y >= 1])
        J = np.zeros((K - 1, K - 1)); J[:, 0] = 1.0                 # d theta_k / d c_m
        for m in range(1, K - 1):
            J[m:, m] = np.exp(c[m])
        g_c = J.T @ g_th
        return nll, -np.concatenate([g_c, g_beta, [g_ls]])

    def start(self):
        cum = np.cumsum(np.bincount(self.y, minlength=self.K))[:-1] / len(self.y)
        th = special.logit(np.clip(cum, 1e-3, 1 - 1e-3))
        c = np.concatenate([[th[0]], np.log(np.maximum(np.diff(th), 1e-2))])
        return np.concatenate([c, np.zeros(self.p), [np.log(0.5)]])

    def fit(self, start=None):
        x0 = self.start() if start is None else start
        res = optimize.minimize(self.negloglik, x0, jac=True, method="L-BFGS-B", options=dict(maxiter=5000, gtol=1e-7))
        K, p = self.K, self.p
        self.res = res
        self.llf = -res.fun
        self.theta = self._theta(res.x[:K - 1])
        self.beta = res.x[K - 1:K - 1 + p]
        self.sigma = float(np.exp(res.x[-1]))
        self.converged = bool(res.success) or np.max(np.abs(res.jac)) < 1e-3
        return self
