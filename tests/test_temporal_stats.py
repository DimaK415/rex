# -*- coding: utf-8 -*-
"""
pytests for TemporalStats
"""
from click.testing import CliRunner
import numpy as np
import os
import pandas as pd
import pytest
from scipy.stats import mode
import tempfile
import traceback

from rex.multi_year_resource import MultiYearWindResource
from rex.renewable_resource import WindResource
from rex.temporal_stats.temporal_stats import (TemporalStats, WaveStats,
                                               weighted_circular_mean)
from rex.temporal_stats.temporal_stats_cli import main
from rex.utilities.loggers import LOGGERS
from rex import TESTDATADIR

PURGE_OUT = True

RES_H5 = os.path.join(TESTDATADIR, 'wtk/ri_100_wtk_2012.h5')
DATASET = 'windspeed_100m'
with WindResource(RES_H5) as f:
    TIME_INDEX = f.time_index
    RES_DATA = f[DATASET]


@pytest.fixture(scope="module")
def runner():
    """
    cli runner
    """
    return CliRunner()


def mode_func(arr, axis=0):
    """
    custom mode stats
    """
    return mode(arr, axis=axis).mode[0]


@pytest.mark.parametrize(("max_workers", "sites"),
                         [(1, slice(None)),
                          (1, slice(None, None, 10)),
                          (1, list(range(20))),
                          (1,
                           np.random.choice(range(100), 20, replace=False)),
                          (None, slice(None)),
                          (None, slice(None, None, 10)),
                          (None, list(range(20))),
                          (None,
                           np.random.choice(range(100), 20, replace=False))])
def test_means(max_workers, sites):
    """
    Test TemporalStats means
    """
    test_stats = TemporalStats.all(RES_H5, DATASET, sites=sites,
                                   statistics='mean',
                                   res_cls=WindResource,
                                   max_workers=max_workers)
    if isinstance(sites, np.ndarray):
        sites = np.sort(sites)

    res_data = RES_DATA[:, sites]
    gids = np.arange(RES_DATA.shape[1], dtype=int)[sites]

    msg = ('gids do not match!')
    assert np.allclose(gids, test_stats.index.values), msg

    truth = np.mean(res_data, axis=0)
    msg = 'Means do not match!'
    assert np.allclose(truth, test_stats['mean'].values), msg

    mask = TIME_INDEX.month == 1
    truth = np.mean(res_data[mask], axis=0)
    msg = 'January means do not match!'
    assert np.allclose(truth, test_stats['Jan_mean'].values), msg

    mask = TIME_INDEX.hour == 0
    truth = np.mean(res_data[mask], axis=0)
    msg = 'Midnight means do not match!'
    assert np.allclose(truth, test_stats['00:00UTC_mean'].values), msg

    mask = (TIME_INDEX.month == 1) & (TIME_INDEX.hour == 0)
    truth = np.mean(res_data[mask], axis=0)
    msg = 'January-midnight means do not match!'
    assert np.allclose(truth, test_stats['Jan-00:00UTC_mean'].values), msg


@pytest.mark.parametrize("max_workers", [1, None])
def test_medians(max_workers):
    """
    Test TemporalStats medians
    """
    test_stats = TemporalStats.all(RES_H5, DATASET,
                                   statistics='median',
                                   res_cls=WindResource,
                                   max_workers=max_workers)

    res_data = RES_DATA.copy()
    gids = np.arange(RES_DATA.shape[1], dtype=int)

    msg = ('gids do not match!')
    assert np.allclose(gids, test_stats.index.values), msg

    truth = np.median(res_data, axis=0)
    msg = 'Medians do not match!'
    assert np.allclose(truth, test_stats['median'].values), msg

    mask = TIME_INDEX.month == 1
    truth = np.median(res_data[mask], axis=0)
    msg = 'January medians do not match!'
    assert np.allclose(truth, test_stats['Jan_median'].values), msg

    mask = TIME_INDEX.hour == 0
    truth = np.median(res_data[mask], axis=0)
    msg = 'Midnight medians do not match!'
    assert np.allclose(truth, test_stats['00:00UTC_median'].values), msg

    mask = (TIME_INDEX.month == 1) & (TIME_INDEX.hour == 0)
    truth = np.median(res_data[mask], axis=0)
    msg = 'January-midnight medians do not match!'
    assert np.allclose(truth, test_stats['Jan-00:00UTC_median'].values), msg


@pytest.mark.parametrize("max_workers", [1, None])
def test_stdevs(max_workers):
    """
    Test TemporalStats stdevs
    """
    test_stats = TemporalStats.all(RES_H5, DATASET,
                                   statistics='std',
                                   res_cls=WindResource,
                                   max_workers=max_workers)

    res_data = RES_DATA.copy()
    gids = np.arange(RES_DATA.shape[1], dtype=int)

    msg = ('gids do not match!')
    assert np.allclose(gids, test_stats.index.values), msg

    truth = np.std(res_data, axis=0)
    msg = 'Stdevs do not match!'
    assert np.allclose(truth, test_stats['std'].values, rtol=0.0001), msg

    mask = TIME_INDEX.month == 1
    truth = np.std(res_data[mask], axis=0)
    msg = 'January stdevs do not match!'
    assert np.allclose(truth, test_stats['Jan_std'].values), msg

    mask = TIME_INDEX.hour == 0
    truth = np.std(res_data[mask], axis=0)
    msg = 'Midnight stdevs do not match!'
    assert np.allclose(truth, test_stats['00:00UTC_std'].values), msg

    mask = (TIME_INDEX.month == 1) & (TIME_INDEX.hour == 0)
    truth = np.std(res_data[mask], axis=0)
    msg = 'January-midnight stdevs do not match!'
    assert np.allclose(truth, test_stats['Jan-00:00UTC_std'].values), msg


@pytest.mark.parametrize("max_workers", [1, None])
def test_custom_stats(max_workers):
    """
    Test custom temporal stats
    """
    stats = {'min': {'func': np.min, 'kwargs': {'axis': 0}},
             'mode': {'func': mode_func, 'kwargs': {'axis': 0}}}
    test_stats = TemporalStats.run(RES_H5, DATASET,
                                   statistics=stats,
                                   res_cls=WindResource,
                                   max_workers=max_workers)

    res_data = RES_DATA.copy()
    gids = np.arange(RES_DATA.shape[1], dtype=int)

    msg = ('gids do not match!')
    assert np.allclose(gids, test_stats.index.values), msg

    truth = np.min(res_data, axis=0)
    msg = 'Mins do not match!'
    assert np.allclose(truth, test_stats['min'].values), msg

    truth = mode(res_data, axis=0).mode[0]
    msg = 'Modes do not match!'
    assert np.allclose(truth, test_stats['mode'].values), msg


@pytest.mark.parametrize("max_workers", [1, None])
def test_multi_year_stats(max_workers):
    """
    Test temporal stats using MultiYearResource
    """
    res_h5 = os.path.join(TESTDATADIR, 'wtk/ri_100_wtk_*.h5')
    with MultiYearWindResource(res_h5) as f:
        res_data = f[DATASET]

    test_stats = TemporalStats.run(res_h5, DATASET,
                                   statistics='mean',
                                   res_cls=MultiYearWindResource,
                                   max_workers=max_workers)

    gids = np.arange(res_data.shape[1], dtype=int)

    msg = ('gids do not match!')
    assert np.allclose(gids, test_stats.index.values), msg

    truth = np.mean(res_data, axis=0)
    msg = 'Means do not match!'
    assert np.allclose(truth, test_stats['mean'].values), msg


@pytest.mark.parametrize("weights", [None, "windspeed_100m"])
def test_weighted_circular_means(weights):
    """
    Test weighted ciruclar means using wave stats class
    """
    dataset = 'winddirection_100m'
    with WindResource(RES_H5) as f:
        res_data = f[dataset]
        if weights is not None:
            norm_weights = f[weights]
            norm_weights = np.exp(norm_weights)
            norm_weights /= np.sum(norm_weights)
        else:
            norm_weights = None

    test_stats = WaveStats.run(RES_H5, dataset,
                               statistics='weighted_circular_mean',
                               res_cls=WindResource,
                               weights=weights)

    gids = np.arange(res_data.shape[1], dtype=int)

    msg = ('gids do not match!')
    assert np.allclose(gids, test_stats.index.values), msg

    truth = weighted_circular_mean(res_data, weights=norm_weights, axis=0)
    msg = 'Circular Means do not match!'
    assert np.allclose(truth, test_stats['weighted_mean'].values), msg


def test_cli(runner):
    """
    Test CLI
    """
    with tempfile.TemporaryDirectory() as td:
        result = runner.invoke(main, ['-h5', RES_H5,
                                      '-dset', DATASET,
                                      '-o', td,
                                      '-mw', 1,
                                      '-res', 'Wind'])
        msg = ('Failed with error {}'
               .format(traceback.print_exception(*result.exc_info)))
        assert result.exit_code == 0, msg

        name = os.path.splitext(os.path.basename(RES_H5))[0]
        out_fpath = '{}_{}.csv'.format(name, DATASET)
        test_stats = pd.read_csv(os.path.join(td, out_fpath))
        res_data = RES_DATA
        gids = np.arange(RES_DATA.shape[1], dtype=int)

        msg = ('gids do not match!')
        assert np.allclose(gids, test_stats.index.values), msg

        truth = np.mean(res_data, axis=0)
        msg = 'Means do not match!'
        assert np.allclose(truth, test_stats['mean'].values), msg

        mask = TIME_INDEX.month == 1
        truth = np.mean(res_data[mask], axis=0)
        msg = 'January means do not match!'
        assert np.allclose(truth, test_stats['Jan_mean'].values), msg

        mask = TIME_INDEX.hour == 0
        truth = np.mean(res_data[mask], axis=0)
        msg = 'Midnight means do not match!'
        assert np.allclose(truth, test_stats['00:00UTC_mean'].values), msg

        mask = (TIME_INDEX.month == 1) & (TIME_INDEX.hour == 0)
        truth = np.mean(res_data[mask], axis=0)
        msg = 'January-midnight means do not match!'
        assert np.allclose(truth, test_stats['Jan-00:00UTC_mean'].values), msg

    LOGGERS.clear()


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
