# Licensed under a 3-clause BSD style license - see LICENSE.rst
from numpy.testing import assert_almost_equal
from ..isrf import Schlickeiser, Galprop

# TODO
def _test_Schlickeiser_omega_g_over_b():
    """ Check that CMB has the energy density it is
    supposed to have according to its temperature """
    actual = Schlickeiser()._omega_g_over_b('CMB')
    assert_almost_equal(actual, 1, places=2)

# TODO
def _test_Schlickeiser_call():
    """ Check that we roughly get the same value
    as in Fig. 3.9 of Hillert's diploma thesis.
    TODO: The check should be made against a published
    value instead """
    actual = Schlickeiser()(1e-3)
    assert_almost_equal(actual / 189946, 1, places=5)


def test_Galprop_call():
    Galprop()
    # TODO