# -*- coding: utf-8 -*-
# pylint: disable=all
"""
pytests for multi time resource handlers
"""
import numpy as np
import os
from pandas.testing import assert_frame_equal
import pytest

from rex import TESTDATADIR
from rex.multi_time_resource import (MultiTimeH5, MultiTimeNSRDB,
                                     MultiTimeWindResource)
from rex.resource import Resource


@pytest.fixture
def MultiTimeNSRDB_res():
    """
    Init NSRDB resource handler
    """
    path = os.path.join(TESTDATADIR, 'nsrdb/ri_100_nsrdb_*.h5')

    return MultiTimeNSRDB(path)


@pytest.fixture
def MultiTimeNSRDB_list_res():
    """
    Init NSRDB resource handler
    """
    files = [os.path.join(TESTDATADIR, 'nsrdb/ri_100_nsrdb_2012.h5'),
             os.path.join(TESTDATADIR, 'nsrdb/ri_100_nsrdb_2013.h5')]

    return MultiTimeNSRDB(files)


@pytest.fixture
def MultiTimeWind_res():
    """
    Init WindResource resource handler
    """
    path = os.path.join(TESTDATADIR, 'wtk/ri_100_wtk_*.h5')

    return MultiTimeWindResource(path)


def check_res(res_cls):
    """
    Run test on len and shape methods
    """
    time_index = None
    for file in res_cls.h5_files:
        with Resource(file) as f:
            if time_index is None:
                time_index = f.time_index
            else:
                time_index = time_index.append(f.time_index)

    with Resource(res_cls.h5_files[0]) as f:
        meta = f.meta

    res_shape = (len(time_index), len(meta))

    assert len(res_cls) == len(time_index)
    assert res_cls.shape == res_shape

    assert np.all(np.isin(['meta', 'time_index'],
                          res_cls.datasets))
    assert np.all(~np.isin(['meta', 'time_index', 'coordinates'],
                           res_cls.resource_datasets))


def check_attrs(res_cls, dset):
    """
    Check dataset attributes extraction
    """
    truth = res_cls.get_attrs(dset=dset)
    test = res_cls.attrs[dset]

    msg = "{} attributes do not match!".format(dset)
    assert truth == test, msg

    truth = res_cls.get_scale_factor(dset)
    test = res_cls.scale_factors[dset]

    msg = "{} scale factors do not match!".format(dset)
    assert truth == test, msg

    truth = res_cls.get_units(dset)
    test = res_cls.units[dset]

    msg = "{} units do not match!".format(dset)
    assert truth == test, msg


def check_properties(res_cls, dset):
    """
    Check dataset properties extraction
    """
    shape, dtype, chunks = res_cls.get_dset_properties(dset)

    test = res_cls.shapes[dset]
    msg = "{} shape does not match!".format(dset)
    assert shape == test, msg

    test = res_cls.dtypes[dset]
    msg = "{} dtype does not match!".format(dset)
    assert dtype == test, msg

    test = res_cls.chunks[dset]
    msg = "{} chunks do not match!".format(dset)
    assert chunks == test, msg


def check_meta(res_cls):
    """
    Run tests on meta data
    """
    with Resource(res_cls.h5_files[0]) as f:
        truth = f.meta

    test = res_cls['meta']
    assert_frame_equal(truth, test, check_dtype=False)

    test = res_cls.lat_lon
    assert np.allclose(truth[['latitude', 'longitude']].values, test)


def check_time_index(res_cls):
    """
    Run tests on time_index
    """
    truth = None
    for file in res_cls.h5_files:
        with Resource(file) as f:
            if truth is None:
                truth = f.time_index
            else:
                truth = truth.append(f.time_index)

    test = res_cls.time_index

    assert np.all(test == truth)


def check_dset(res_cls, ds_name):
    """
    Run tests on dataset ds_name
    """
    truth = []
    for file in res_cls.h5_files:
        truth.append(res_cls.h5._h5_map[file][ds_name])

    truth = np.concatenate(truth, axis=0)

    test = res_cls[ds_name]
    assert np.allclose(truth, test)

    test = res_cls[ds_name, :, 10]
    assert np.allclose(truth[:, 10], test)

    test = res_cls[ds_name, :, 10:20]
    assert np.allclose(truth[:, 10:20], test)

    test = res_cls[ds_name, :, [1, 3, 5, 7]]
    assert np.allclose(truth[:, [1, 3, 5, 7]], test)

    test = res_cls[ds_name, :, [2, 6, 3, 20]]
    assert np.allclose(truth[:, [2, 6, 3, 20]], test)


def test_time_index_error():
    """
    Test time_index RuntimeError when file time_index overlap
    """
    path = os.path.join(TESTDATADIR, 'wtk/wtk_2010_*m.h5')
    with pytest.raises(RuntimeError):
        with MultiTimeWindResource(path) as f:
            f.time_index  # pylint: disable=pointless-statement


class TestMultiTimeNSRDB:
    """
    Multi Year NSRDB Resource handler tests
    """
    @staticmethod
    def test_res(MultiTimeNSRDB_res):
        """
        test NSRDB class calls
        """
        check_res(MultiTimeNSRDB_res)
        MultiTimeNSRDB_res.close()

    @staticmethod
    def test_meta(MultiTimeNSRDB_res):
        """
        test extraction of NSRDB meta data
        """
        check_meta(MultiTimeNSRDB_res)
        MultiTimeNSRDB_res.close()

    @staticmethod
    def test_time_index(MultiTimeNSRDB_res):
        """
        test extraction of NSRDB time_index
        """
        check_time_index(MultiTimeNSRDB_res)
        MultiTimeNSRDB_res.close()

    @staticmethod
    def test_ds(MultiTimeNSRDB_res, ds_name='dni'):
        """
        test extraction of a variable array, attributes, and properties
        """
        check_dset(MultiTimeNSRDB_res, ds_name)
        check_attrs(MultiTimeNSRDB_res, ds_name)
        check_properties(MultiTimeNSRDB_res, ds_name)
        MultiTimeNSRDB_res.close()


class TestMultiTimeList:
    """
    Test multi time resource handler from list of files
    """
    @staticmethod
    def test_res(MultiTimeNSRDB_list_res):
        """
        test NSRDB class calls
        """
        check_res(MultiTimeNSRDB_list_res)
        MultiTimeNSRDB_list_res.close()

    @staticmethod
    def test_meta(MultiTimeNSRDB_list_res):
        """
        test extraction of NSRDB meta data
        """
        check_meta(MultiTimeNSRDB_list_res)
        MultiTimeNSRDB_list_res.close()

    @staticmethod
    def test_time_index(MultiTimeNSRDB_list_res):
        """
        test extraction of NSRDB time_index
        """
        check_time_index(MultiTimeNSRDB_list_res)
        MultiTimeNSRDB_list_res.close()

    @staticmethod
    def test_ds(MultiTimeNSRDB_list_res, ds_name='dni'):
        """
        test extraction of a variable array, attributes, and properties
        """
        check_dset(MultiTimeNSRDB_list_res, ds_name)
        check_attrs(MultiTimeNSRDB_list_res, ds_name)
        check_properties(MultiTimeNSRDB_list_res, ds_name)
        MultiTimeNSRDB_list_res.close()


class TestMultiTimeWindResource:
    """
    Multi Year WindResource Resource handler tests
    """
    @staticmethod
    def test_res(MultiTimeWind_res):
        """
        test WindResource class calls
        """
        check_res(MultiTimeWind_res)
        MultiTimeWind_res.close()

    @staticmethod
    def test_meta(MultiTimeWind_res):
        """
        test extraction of WindResource meta data
        """
        check_meta(MultiTimeWind_res)
        MultiTimeWind_res.close()

    @staticmethod
    def test_time_index(MultiTimeWind_res):
        """
        test extraction of WindResource time_index
        """
        check_time_index(MultiTimeWind_res)
        MultiTimeWind_res.close()

    @staticmethod
    def test_ds(MultiTimeWind_res, ds_name='windspeed_100m'):
        """
        test extraction of a variable array, attributes, and properties
        """
        check_dset(MultiTimeWind_res, ds_name)
        check_attrs(MultiTimeWind_res, ds_name)
        check_properties(MultiTimeWind_res, ds_name)
        MultiTimeWind_res.close()

    @staticmethod
    def test_new_hubheight(MultiTimeWind_res, ds_name='windspeed_90m'):
        """
        test extraction of interpolated hub-height
        """
        check_dset(MultiTimeWind_res, ds_name)
        MultiTimeWind_res.close()


def test_map_hsds_files():
    """
    Test map hsds files method
    """
    files = [f'/nrel/US_wave/West_Coast/West_Coast_wave_{year}.h5'
             for year in range(1979, 2011)]
    hsds_kwargs = {'endpoint': 'https://developer.nrel.gov/api/hsds',
                   'api_key': 'oHP7dGu4VZeg4rVo8PZyb5SVmYigedRHxi3OfiqI'}
    path = '/nrel/US_wave/West_Coast/West_Coast_wave_*.h5'
    hsds_fps = MultiTimeH5._get_file_paths(path, hsds=True,
                                           hsds_kwargs=hsds_kwargs)

    missing = [f for f in files if f not in hsds_fps]
    wrong = [f for f in hsds_fps if f not in files]
    assert not any(missing), 'Missed files: {}'.format(missing)
    assert not any(wrong), 'Wrong files: {}'.format(wrong)


def execute_pytest(capture='all', flags='-rapP'):
    """Execute module as pytest with detailed summary report.

    Parameters
    ----------
    capture : str
        Log or stdout/stderr capture option. ex: log (only logger),
        all (includes stdout/stderr)
    flags : str
        Which tests to show logs and results for.
    """

    fname = os.path.basename(__file__)
    pytest.main(['-q', '--show-capture={}'.format(capture), fname, flags])


if __name__ == '__main__':
    execute_pytest()
