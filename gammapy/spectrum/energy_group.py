# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""Spectrum energy bin grouping.

There are three classes:

* SpectrumEnergyGroup - one group
* SpectrumEnergyGroups - one grouping, i.e. collection of groups
* SpectrumEnergyGroupMaker - algorithms to compute groupings.

Algorithms to compute groupings are both on SpectrumEnergyGroups and SpectrumEnergyGroupMaker.
The difference is that SpectrumEnergyGroups contains the algorithms and book-keeping that
just have to do with the groups, whereas SpectrumEnergyGroupMaker also accesses
information from SpectrumObservation (e.g. safe energy range or counts data) and
implements higher-level algorithms.
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from collections import OrderedDict
from copy import deepcopy
import numpy as np
from ..extern.six.moves import UserList
import astropy.units as u
from astropy.units import Quantity
from astropy.table import Table
from astropy.table import vstack as table_vstack
from ..utils.table import table_from_row_data, table_row_to_dict

__all__ = [
    'SpectrumEnergyGroup',
    'SpectrumEnergyGroups',
    'SpectrumEnergyGroupMaker',
]


class SpectrumEnergyGroup(object):
    """Spectrum energy group.

    Represents a consecutive range of bin indices (both ends inclusive).
    """
    fields = [
        'energy_group_idx', 'bin_idx_min', 'bin_idx_max',
        'bin_type', 'energy_min', 'energy_max',
    ]
    """List of data members of this class."""

    valid_bin_types = ['normal', 'underflow', 'overflow']
    """Valid values for ``bin_types`` attribute."""

    def __init__(self, energy_group_idx, bin_idx_min, bin_idx_max, bin_type,
                 energy_min, energy_max):
        self.energy_group_idx = energy_group_idx
        self.bin_idx_min = bin_idx_min
        self.bin_idx_max = bin_idx_max
        if bin_type not in self.valid_bin_types:
            raise ValueError('Invalid bin type: {}'.format(bin_type))
        self.bin_type = bin_type
        self.energy_min = Quantity(energy_min)
        self.energy_max = Quantity(energy_max)

    @classmethod
    def from_dict(cls, data):
        data = dict((_, data[_]) for _ in cls.fields)
        return cls(**data)

    @property
    def _data(self):
        return [(_, getattr(self, _)) for _ in self.fields]

    def __repr__(self):
        txt = ['{}={!r}'.format(k, v) for k, v in self._data]
        return '{}({})'.format(self.__class__.__name__, ', '.join(txt))

    def __eq__(self, other):
        return self.to_dict() == other.to_dict()

    def to_dict(self):
        return OrderedDict(self._data)

    @property
    def bin_idx_array(self):
        """Numpy array of bin indices in the group."""
        return np.arange(self.bin_idx_min, self.bin_idx_max + 1)

    @property
    def bin_table(self):
        """Create `~astropy.table.Table` with bins in the group.

        Columns are: ``energy_group_idx``, ``bin_idx``, ``bin_type``
        """
        table = Table()
        table['bin_idx'] = self.bin_idx_array
        table['energy_group_idx'] = self.energy_group_idx
        table['bin_type'] = self.bin_type
        table['energy_min'] = self.energy_min
        table['energy_max'] = self.energy_max
        return table

    def contains_energy(self, energy):
        """Does this group contain a given energy?"""
        return (self.energy_min <= energy) & (energy < self.energy_max)


class SpectrumEnergyGroups(UserList):
    """List of `~gammapy.spectrum.SpectrumEnergyGroup` objects.

    A helper class used by the `gammapy.spectrum.SpectrumEnergyGroupsMaker`.
    """

    def __repr__(self):
        return '{}(len={})'.format(self.__class__.__name__, len(self))

    def __str__(self):
        ss = '{}:\n'.format(self.__class__.__name__)
        lines = self.to_group_table().pformat(max_width=-1, max_lines=-1)
        ss += '\n'.join(lines)
        return ss + '\n'

    def copy(self):
        """Deep copy"""
        return deepcopy(self)

    @classmethod
    def from_total_table(cls, table):
        """Create list of SpectrumEnergyGroup objects from table."""
        groups = cls()

        for energy_group_idx in np.unique(table['energy_group_idx']):
            mask = table['energy_group_idx'] == energy_group_idx
            group_table = table[mask]
            bin_idx_min = group_table['bin_idx'][0]
            bin_idx_max = group_table['bin_idx'][-1]
            if len(set(group_table['bin_type'])) > 1:
                raise ValueError('Inconsistent bin_type within group.')
            bin_type = group_table['bin_type'][0]
            energy_min = group_table['energy_min'].quantity[0]
            energy_max = group_table['energy_max'].quantity[-1]

            group = SpectrumEnergyGroup(
                energy_group_idx=energy_group_idx,
                bin_idx_min=bin_idx_min,
                bin_idx_max=bin_idx_max,
                bin_type=bin_type,
                energy_min=energy_min,
                energy_max=energy_max,
            )
            groups.append(group)

        return groups

    @classmethod
    def from_group_table(cls, table):
        """Create from energy groups in `~astropy.table.Table` format."""
        return cls([
            SpectrumEnergyGroup.from_dict(table_row_to_dict(row))
            for row in table
        ])

    def to_total_table(self):
        """Table with one energy bin per row (`~astropy.table.Table`).

        Columns:

        * ``energy_group_idx`` - Energy group index (int)
        * ``bin_idx`` - Energy bin index (int)
        * ``bin_type`` - Bin type {'normal', 'underflow', 'overflow'} (str)

        There are no energy columns, because the per-bin energy info
        was lost during grouping.
        """
        tables = [group.bin_table for group in self]
        return table_vstack(tables)

    def to_group_table(self):
        """Table with one energy group per row (`~astropy.table.Table`).

        Columns:

        * ``energy_group_idx`` - Energy group index (int)
        * ``energy_group_n_bins`` - Number of bins in the energy group (int)
        * ``bin_idx_min`` - First bin index in the energy group (int)
        * ``bin_idx_max`` - Last bin index in the energy group (int)
        * ``bin_type`` - Bin type {'normal', 'underflow', 'overflow'} (str)
        * ``energy_min`` - Energy group start energy (Quantity)
        * ``energy_max`` - Energy group end energy (Quantity)
        """
        rows = [group.to_dict() for group in self]
        table = table_from_row_data(rows)
        return table

    @property
    def energy_range(self):
        """Total energy range (`~astropy.units.Quantity` of length 2)."""
        return Quantity([self[0].energy_min, self[-1].energy_max])

    @property
    def energy_bounds(self):
        """Energy group bounds (`~astropy.units.Quantity`)."""
        energy = [_.energy_min for _ in self]
        energy.append(self[-1].energy_max)
        return Quantity(energy)

    def find_list_idx(self, energy):
        """Find the list index corresponding to a given energy."""
        for idx, group in enumerate(self):
            if group.contains_energy(energy):
                return idx

        raise IndexError('No group found with energy: {}'.format(energy))


class SpectrumEnergyGroupMaker(object):
    """Energy bin groups for spectral analysis.

    This class contains both methods that run algorithms
    that compute groupings as well as the results as data members
    and methods to debug and assess the results.

    The input ``obs`` is used read-only, to access the counts energy
    binning, as well as some other info that is used for energy bin grouping.

    Parameters
    ----------
    obs : `~gammapy.spectrum.SpectrumObservation`
        Spectrum observation

    Attributes
    ----------
    obs : `~gammapy.spectrum.SpectrumObservation`
        Spectrum observation data
    groups : `~gammapy.spectrum.SpectrumEnergyGroups`
        List of energy groups

    See also
    --------
    SpectrumEnergyGroups, SpectrumEnergyGroup, FluxPointEstimator
    """

    def __init__(self, obs):
        self.obs = obs
        self.groups = None

    def groups_from_obs(self):
        """Compute energy groups list with one group per energy bin.

        Parameters
        ----------
        obs : `~gammapy.spectrum.SpectrumObservation`
            Spectrum observation data

        Returns
        -------
        groups : `~gammapy.spectrum.SpectrumEnergyGroups`
            List of energy groups
        """
        ebounds_obs = self.obs.e_reco
        size = ebounds_obs.nbins
        table = Table()
        table['bin_idx'] = np.arange(size)
        table['energy_group_idx'] = np.arange(size)
        table['bin_type'] = ['normal'] * size
        table['energy_min'] = ebounds_obs.lower_bounds
        table['energy_max'] = ebounds_obs.upper_bounds
        self.groups = SpectrumEnergyGroups.from_total_table(table)

    def compute_groups_fixed(self, ebounds):
        """Apply grouping for a given fixed energy binning.

        Parameters
        ----------
        ebounds : `~astropy.units.Quantity`
            Energy bounds array
        """
        ebounds_obs = self.obs.e_reco
        groups = []

        # Calculate all differences between `ebounds` and `ebounds_obs`
        # Find the indices where the sign changes
        energy_binning_offset = ebounds - 1 * u.MeV
        diff = energy_binning_offset[:, np.newaxis] - ebounds_obs.lower_bounds
        lower_indices = np.argmin(np.sign(diff), axis=1)
        # Make sure the last bin is not the first bin.
        if lower_indices[-1] == 0:
            lower_indices[-1] = ebounds_obs.nbins

        energy_group_idx = 0

        if lower_indices[0] > 0:
            # Create underflow group
            group = SpectrumEnergyGroup(
                energy_group_idx=energy_group_idx,
                bin_idx_min=0,
                bin_idx_max=lower_indices[0] - 1,
                bin_type='underflow',
                energy_min=ebounds_obs.lower_bounds[0],
                energy_max=ebounds_obs.upper_bounds[lower_indices[0] - 1],
            )
            groups.append(group)
            energy_group_idx += 1

        # Create normal groups (could be none)
        for index in range(len(ebounds) - 1):
            group = SpectrumEnergyGroup(
                energy_group_idx=energy_group_idx,
                bin_idx_min=lower_indices[index],
                bin_idx_max=lower_indices[index + 1] - 1,
                bin_type='normal',
                energy_min=ebounds_obs.lower_bounds[lower_indices[index]],
                energy_max=ebounds_obs.upper_bounds[lower_indices[index + 1] - 1],
            )
            groups.append(group)
            energy_group_idx += 1

        maxbin = lower_indices[-1]
        if maxbin < ebounds_obs.nbins:
            # Create overflow group
            group = SpectrumEnergyGroup(
                energy_group_idx=energy_group_idx,
                bin_idx_min=maxbin,
                bin_idx_max=ebounds_obs.nbins - 1,
                bin_type='overflow',
                energy_min=ebounds_obs.lower_bounds[maxbin],
                energy_max=ebounds_obs.upper_bounds[-1])
            groups.append(group)

        self.groups = SpectrumEnergyGroups(groups)
