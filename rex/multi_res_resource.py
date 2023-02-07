# -*- coding: utf-8 -*-
"""
Classes to handle resource data at multiple spatiotemporal resolutions
"""
import numpy as np
import pandas as pd
import os
import copy
import logging
from scipy.spatial import KDTree
import warnings

from rex.utilities.parse_keys import parse_keys
from rex.utilities.exceptions import ResourceRuntimeError

logger = logging.getLogger(__name__)


class MultiResolutionResource:
    """Multi-resolution resource handler. Uses two resource handlers for files
    at two different spatiotemporal resolutions, and then interpolates the
    lower resolution data to the higher resolution data on the fly.
    """

    HR_ATTRS = ('meta', 'time_index', 'coordinates', 'lat_lon', 'data_version',
                'global_attrs', 'get_meta_arr')
    """Attributes that are always taken only from the high-res data handler"""

    def __init__(self, hr_res, lr_res, nn_map=None, nn_d=None):
        """
        Parameters
        ----------
        hr_res : Resource | MultiFileResource | MultiYearResource
            rex resource handler for the high-resolution data. All retrieval
            gid's are based on this dataset, and the lr_res data is mapped to
            this.
        lr_res : Resource | MultiFileResource | MultiYearResource
            rex resource handler for the low-resolution data. The data from
            this handler is mapped to the hr_res data.
        nn_map : np.ndarray
            Optional 1D array of nearest neighbor mappings. This will be
            created if not provided. This is created by making a kdtree of the
            lr_res coords and then querying with the hr_res coords. As an
            example, nn_map[10] will return the lr_res index corresponding to
            gid 10 from the hr_res data
        nn_d : np.ndarray
            Optional 1D array of nearest neighbor distances. This will be
            created if not provided. This is created by making a kdtree of the
            lr_res coords and then querying with the hr_res coords. As an
            example, nn_map[10] will return the distance between hr_res gid=10
            and the corresponding lr_res site
        """

        msg = ('The hr_res and lr_res classes need to be the same but '
               'received: {} and {}'
               .format(hr_res.__class__, lr_res.__class__))
        assert hr_res.__class__ == lr_res.__class__, msg

        self._hr_res = hr_res
        self._lr_res = lr_res
        self._nn_map = nn_map
        self._nn_d = nn_d

        if self._nn_map is None:
            self._nn_d, self._nn_map = self.make_nn_map(hr_res, lr_res)

    @staticmethod
    def make_nn_map(hr_res, lr_res):
        """Make the low-res-to-high-res resource nearest neighbor mapping

        Parameters
        ----------
        hr_res : Resource | MultiFileResource | MultiYearResource
            rex resource handler for the high-resolution data. All retrieval
            gid's are based on this dataset, and the lr_res data is mapped to
            this.
        lr_res : Resource | MultiFileResource | MultiYearResource
            rex resource handler for the low-resolution data. The data from
            this handler is mapped to the hr_res data.

        Returns
        -------
        nn_d : np.ndarray
            Optional 1D array of nearest neighbor distances. This will be
            created if not provided. This is created by making a kdtree of the
            lr_res coords and then querying with the hr_res coords. As an
            example, nn_map[10] will return the distance between hr_res gid=10
            and the corresponding lr_res site
        nn_map : np.ndarray
            Optional 1D array of nearest neighbor mappings. This will be
            created if not provided. This is created by making a kdtree of the
            lr_res coords and then querying with the hr_res coords. As an
            example, nn_map[10] will return the lr_res index corresponding to
            gid 10 from the hr_res data
        """
        tree = KDTree(lr_res.coordinates)
        nn_d, nn_map = tree.query(hr_res.coordinates)
        return nn_d, nn_map

    def map_ds_slice(self, ds_slice):
        """Map the requested dataset slice from high-res spatial indices to
        low-res spatial indices

        Parameters
        ----------
        ds_slice : tuple
            Tuple where each entry is a slice or list index argument for the
            respective axis, e.g. (slice(None), [0, 2]) retrieves the full
            axis=0 and indices 0 and 2 from axis=1.

        Returns
        -------
        ds_slice : tuple
            Tuple where each entry is a slice or list index argument for the
            respective axis, e.g. (slice(None), [0, 2]) retrieves the full
            axis=0 and indices 0 and 2 from axis=1.
            The returned value is now low-res spatial indices using simple
            nearest neighbor.
        """

        if len(ds_slice) == 1:
            ds_slice = ds_slice + (slice(None), )

        elif len(ds_slice) > 2:
            msg = 'Cannot handle ds_slice > 2D'
            logger.error(msg)
            raise ResourceRuntimeError(msg)

        t_slice, s_slice = ds_slice
        s_slice = self._nn_map[s_slice]
        return (t_slice, s_slice)

    def time_interp(self, arr):
        """Perform temporal interpolation on the low-res data to match the
        high-res data.

        Parameters
        ----------
        arr : np.ndarray
            2D array with shape (time, sites) where time corresponds to the
            low-resolution resource.

        Returns
        -------
        arr : np.ndarray
            2D array with shape (time, sites) where the time axis has been
            linearly interpolated to the high-resolution time index.
        """
        arr = pd.DataFrame(arr, index=self._lr_res.time_index)
        arr = arr.reindex(self._hr_res.time_index)
        arr = arr.interpolate('linear').ffill().bfill()
        return arr.values

    def __repr__(self):
        msg = "{} for {}".format(self.__class__.__name__, self.h5_file)

        return msg

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._hr_res.close()
        self._lr_res.close()
        if type is not None:
            raise

    def __len__(self):
        return len(self._hr_res)

    def __getitem__(self, keys):
        ds, ds_slice = parse_keys(keys)
        _, ds_name = os.path.split(ds)

        if ds_name.startswith('time_index'):
            out = self._hr_res._get_time_index(ds, ds_slice)

        elif ds_name.startswith('meta'):
            out = self._hr_res._get_meta(ds, ds_slice)

        elif ds_name.startswith('coordinates'):
            out = self._hr_res._get_coords(ds, ds_slice)

        elif 'SAM' in ds_name:
            site = ds_slice[0]
            if isinstance(site, (int, np.integer)):
                out = self.get_SAM_df(site)  # pylint: disable=E1111
            else:
                msg = "Can only extract SAM DataFrame for a single site"
                raise ResourceRuntimeError(msg)

        elif ds_name in self._hr_res.resource_datasets:
            out = self._hr_res._get_ds(ds, ds_slice)

        elif ds_name in self._lr_res.resource_datasets:
            ds_slice = self.map_ds_slice(ds_slice)
            out = self._lr_res._get_ds(ds, ds_slice)
            out = self.time_interp(out)

        return out

    def __iter__(self):
        return self

    def __next__(self):
        if self._i >= len(self.datasets):
            self._i = 0
            raise StopIteration

        dset = self.datasets[self._i]
        self._i += 1

        return dset

    def __contains__(self, dset):
        return dset in self.datasets

    def __getattr__(self, attr):
        if attr in dir(self):
            return getattr(self, attr)
        if attr in self.HR_ATTRS:
            return getattr(self._hr_res, attr)
        else:
            try:
                hr_attr = getattr(self._hr_res, attr)
                lr_attr = getattr(self._lr_res, attr)
                if isinstance(hr_attr, list) and isinstance(lr_attr, list):
                    return list(set(hr_attr + lr_attr))
                elif isinstance(hr_attr, tuple) and isinstance(lr_attr, tuple):
                    return hr_attr + lr_attr
                elif isinstance(hr_attr, dict) and isinstance(lr_attr, dict):
                    out = copy.deepcopy(lr_attr)
                    out.update(hr_attr)
                    return out
            except Exception as e:
                msg = ('Could not retrieve attribute "{}" from '
                       'MultiResolutionResource handler, the hr and lr '
                       'handler attributes could not be combined: {} {}'
                       .format(attr, hr_attr, lr_attr))
                logger.error(msg)
                raise RuntimeError(msg) from e

    def _preload_SAM(self, *args, **kwargs):
        """
        """

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            hr_sam = self._hr_res._preload_SAM(*args, **kwargs)
            hr_sites = args[0]
            lr_sites = [self._nn_map[i] for i in hr_sites]
            args = (lr_sites,) + args[1:]
            lr_sam = self._lr_res._preload_SAM(*args, **kwargs)

        return hr_sam
