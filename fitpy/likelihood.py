import numpy as np
from scipy.optimize import minimize
from scipy.stats import chi2
from abc import ABC, abstractmethod


def get_confidence_ellipse(center: np.ndarray, cova: np.ndarray, nsigma: int = 1, npoints: int = 100) -> np.ndarray:
    """
    Return the coordinates of a covariance ellipse.

    Args:
        center (np.ndarray): The center of the ellipse.
        cova (np.ndarray): The covariance matrix.
        nsigma (int, optional): The number of standard deviations for the ellipse. Defaults to 1.
        npoints (int, optional): The number of points to generate on the ellipse. Defaults to 1000.

    Returns:
        np.ndarray: The coordinates of the ellipse.
    """
    cholesky_l = np.linalg.cholesky(cova)
    t = np.linspace(0, 2 * np.pi, npoints)
    circle = np.column_stack([np.cos(t), np.sin(t)])
    ellipse = nsigma * circle @ cholesky_l.T + center
    return ellipse.T


class LikelihoodFit(ABC):

    def __init__(self, x, y, model):
        self.x = x
        self.y = y
        self.model = model

    @abstractmethod
    def cost_function(self, par):
        pass

    # Vectorized version of the cost function useful for plotting
    def vcost_function(self, parx_index, pary_index, parx, pary):

        vcost = []
        for y in pary:
            for x in parx:
                par = self.get_estimators().copy()
                par[parx_index] = x
                par[pary_index] = y
                cost1 = self.cost_function(par)
                vcost.append(cost1)

        vcost = np.reshape(vcost, newshape=(len(pary), len(parx)))
        return vcost

    def __call__(self, seed):
        self.fit_result = minimize(self.cost_function, x0=seed)

        if not self.fit_result.success:
            print(self.fit_result)
            raise FloatingPointError("ERROR: scipy.optimize.minimize did not converge")

        return self.fit_result.status

    # Fit results getters
    def get_estimators(self):
        return self.fit_result.x

    def get_errors(self):
        covariance = self.get_covariance_matrix()
        errors = np.sqrt(np.diagonal(covariance))
        return errors

    def get_covariance_matrix(self):
        covariance = 2 * self.fit_result.hess_inv
        return covariance

    def get_confidence_ellipse(self, xindex, yindex, nsigma: int = 1, npoints: int = 100):
        estimators = self.get_estimators()
        estimator_pair = estimators[[xindex, yindex]]
        cova = self.get_covariance_matrix()
        cova_pair = cova[np.ix_([xindex, yindex], [xindex, yindex])]
        return get_confidence_ellipse(estimator_pair, cova_pair, nsigma, npoints)

    def get_correlation_matrix(self):
        covariance = self.get_covariance_matrix()
        errors = self.get_errors()
        correlation = covariance / np.tensordot(errors, errors, axes=0)
        return correlation

    def get_deviance(self):
        return self.fit_result.fun

    def get_ndof(self):
        estimators = self.get_estimators()
        ndof = len(self.x) - len(estimators)
        return ndof

    def get_pvalue(self):
        deviance = self.get_deviance()
        ndof = self.get_ndof()
        pvalue = chi2.sf(deviance, ndof)
        return pvalue

    def get_minimize_result(self):
        return self.fit_result

    def get_yfit(self, x):
        estimators = self.get_estimators()
        return self.model(x, estimators) 

    def get_yfit_error(self, x):

        gradient = self.get_gradient(x)

        # Propagate parameter errors
        covariance = self.get_covariance_matrix()
        var_yfit = np.einsum("ik,ij,jk->k", gradient, covariance, gradient)
        sigma_yfit = np.sqrt(var_yfit)
        
        return sigma_yfit

    # Numerical derivative of the model wrt the parameters evaluated at the estimators
    """
    Arguments:
        x (np.array): values of the independent variable at which the gradient will be evaluated
    Return: 
        gradient (np.array):  2 dimensional array containing the calculated gradient. 
            The first dimension corresponds to the parameters and the second one to the values of 
            the independent variable
    """
    def get_gradient(self, x):

        estimators = self.get_estimators()
        errors = self.get_errors()

        # Setting finite difference steps to some fraction of the errors
        delta_fraction = 0.01
        steps = errors * delta_fraction
        ndimensions = len(steps)

        gradient = []
        for i in range(ndimensions):

            step1 = steps[i]

            # Change an element of the parameter vector by step
            delta_par1 = np.zeros_like(steps)
            delta_par1[i] = step1
            par_down = estimators - delta_par1
            par_up = estimators + delta_par1

            # Calculate an element of the gradient vector
            model_up = self.model(x, par_up)
            model_down = self.model(x, par_down)
            gradient1 = (model_up - model_down) / (2 * step1)
            gradient.append(gradient1)

        return gradient


class LeastSquares(LikelihoodFit):

    def __init__(self, x, y, ysigma, model):
        LikelihoodFit.__init__(self, x, y, model)
        self.ysigma = ysigma

    def cost_function(self, par):
        mu = self.model(self.x, par)
        residuals = (self.y - mu) / self.ysigma
        cost = np.sum(residuals**2)
        return cost



class Poisson(LikelihoodFit):

    def __init__(self, x, y, model):
        LikelihoodFit.__init__(self, x, y, model)


    # Poisson cost function
    def cost_function(self, par):

        mu = self.model(self.x, par)

        # Piecewise-defined  function for case y!=0 and y=0

        # Select data points y!=0
        zero_mask = (self.y == 0)
        y1 = np.ma.array(self.y, mask=zero_mask)
        mu1 = np.ma.array(mu, mask=zero_mask)
        cost_array1 = 2 * (mu1 - y1) - 2 * y1 * np.log(mu1 / y1)
        cost1 = cost_array1.sum()

        # Select data points y=0
        mu2 = np.ma.array(mu, mask=np.logical_not(zero_mask))
        cost_array2 = 2 * mu2
        cost2 = cost_array2.sum()

        cost = cost1 + cost2

        return cost
