# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import absolute_import, division, print_function, unicode_literals
import pytest
import numpy as np
from numpy.testing.utils import assert_allclose
from astropy.convolution import Gaussian2DKernel
from ...utils.testing import requires_dependency, requires_data
from ...maps import Map
from ...detect import TSMapEstimator


@pytest.fixture
def input_maps(scope='session'):
    filename = '$GAMMAPY_EXTRA/test_datasets/unbundled/poisson_stats_image/input_all.fits.gz'
    maps = {}
    maps['counts'] = Map.read(filename, hdu='counts')
    maps['exposure'] = Map.read(filename, hdu='exposure')
    maps['background'] = Map.read(filename, hdu='background')
    return maps


@requires_dependency('scipy')
@requires_dependency('skimage')
@requires_data('gammapy-extra')
def test_compute_ts_map(input_maps):
    """Minimal test of compute_ts_image"""
    kernel = Gaussian2DKernel(5)

    ts_estimator = TSMapEstimator(method='leastsq iter', n_jobs=4)
    result = ts_estimator.run(input_maps, kernel=kernel)

    assert_allclose(result['ts'].data[99, 99], 1714.23, rtol=1e-2)
    assert_allclose(result['niter'].data[99, 99], 3)
    assert_allclose(result['flux'].data[99, 99], 1.02e-09, rtol=1e-2)
    assert_allclose(result['flux_err'].data[99, 99], 3.84e-11, rtol=1e-2)
    assert_allclose(result['flux_ul'].data[99, 99], 1.10e-09, rtol=1e-2)

@requires_dependency('scipy')
@requires_dependency('skimage')
@requires_data('gammapy-extra')
def test_compute_ts_map_downsampled(input_maps):
    """Minimal test of compute_ts_image"""
    kernel = Gaussian2DKernel(2.5)

    ts_estimator = TSMapEstimator(method='root brentq', n_jobs=4)
    result = ts_estimator.run(input_maps, kernel=kernel, downsampling_factor=2)

    assert_allclose(result['ts'].data[99, 99], 1675.28, rtol=1e-2)
    assert_allclose(result['niter'].data[99, 99], 7)
    assert_allclose(result['flux'].data[99, 99], 1.02e-09, rtol=1e-2)
    assert_allclose(result['flux_err'].data[99, 99], 3.84e-11, rtol=1e-2)
    assert_allclose(result['flux_ul'].data[99, 99], 1.10e-09, rtol=1e-2)

