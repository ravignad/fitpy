# Fit the cosmic ray spectrum with a non-linear least squares fit

import numpy as np

# Install likefit if not available with: pip -m install likefit
import likefit

# Data binned in $xdata = log_{10}(E/eV)$, ydata = number of cosmic rays in the energy bin
xdata = np.linspace(18.45, 20.45, 21)
ydata = np.array([13023, 7711, 4478, 3159, 2162, 1483, 1052, 699, 451, 323, 200, 110, 43, 28, 23, 5, 2, 0, 1, 0, 0])
ysigma = np.sqrt(ydata)

# Select the bins to fit
xfit = xdata[3:11]
yfit = ydata[3:11]
yfit_sigma = ysigma[3:11]


# Fit model
def fit_model(x, par):
    return np.power(10, par[0]-par[1]*(x-19))


# Fit data
fitter = likefit.NonLinearLeastSquares(xfit, yfit, yfit_sigma, fit_model)
seed = np.array([3, 2])

# Reduce the tolerance to converge the minimization
fitter.fit(seed, tol=1e-3)
fitter.print_results()

# Plot data and fit
fitter.plot_fit()

# Plot the 1σ, 2σ, and 3σ confidence regions
fitter.plot_confidence_regions(parx_index=0, pary_index=1, parx_name="a", pary_name="b", nsigma=3)
