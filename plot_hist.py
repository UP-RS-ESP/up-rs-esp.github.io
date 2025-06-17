
from collections.abc import Iterable

import numpy as np
import matplotlib.pyplot as plt


def plot_hist(x, bins=10, log_bins=False, density=False, ax=None, **kwargs):
    """Plot a histogram (or pdf) of x.

    Compute and plot the histogram (or probability density) of x. Keyword
    arguments are passed to plt.plot. See parameters and ``np.histogram``
    for details.

    Parameters
    ----------
    x : array_like
        The data from which a frequency distribution is plot.

    bins : int or array_like, optional (default=10)
        If ``bins`` is an int, it determines the number of bins to create.
        If ``log_bins`` is True, this number determines the (approximate)
        number of bins to create for each magnitude. For linear bins, it is
        the number of bins for the whole range of values. If ``bins`` is a
        sequence, it defines the bin edges, including the rightmost edge,
        allowing for non-uniform bin widths.

    log_bins : bool, optional (default=False)
        Whether to use logarithmically or linearly spaced bins.

    density : bool, optional (default=False)
        If False, the result will contain the number of samples in each
        bin.  If True, the result is the value of the probability *density*
        function at the bin, normalized such that the *integral* over the
        range is 1. Note that the sum of the histogram values will not be
        equal to 1 unless bins of unity width are chosen; it is not a
        probability *mass* function.

    ax : matplotlib axes object, optional (default=None)
        An axes instance to use.

    Returns
    -------
    ax : matplotlib axes object
        A matplotlib axes instance.

    hist : np.ndarray
        The values of the histogram. See ``density``.

    bin_edges : np.ndarray
        The edges of the bins.

    """

    # create bins
    if isinstance(bins, Iterable):
        bin_edges = bins
    else:
        bin_edges = _create_bin_edges(x, bins, log_bins)

    # counts and bin_centers
    hist, _ = np.histogram(x, bin_edges, density=density)
    hist = hist.astype(float)
    hist[hist == 0] = np.nan
    bin_centers = (bin_edges[1:] + bin_edges[:-1]) / 2.

    # plot
    if ax is None:
        _, ax = plt.subplots()

    ax.plot(bin_centers, hist, **kwargs)

    # set scale
    if log_bins:
        ax.set_xscale('log')

    return ax, hist, bin_edges
    
    
def _create_bin_edges(x, bins, log_bins):

        xmax = x.max()
        xmin = x.min()
        if log_bins is False:
            bin_edges = np.linspace(xmin, xmax, bins)
        else:
            log_xmin = np.log10(xmin)
            log_xmax = np.log10(xmax)
            bins = int(np.ceil((log_xmax - log_xmin) * bins))
            bin_edges = np.logspace(log_xmin, log_xmax, bins)

        return bin_edges
