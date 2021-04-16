"""
btsf.util

A module with helper functions to work with btsf data,
typically acting on a BinaryTimeSeriesFile instance.
"""

from typing import Union

from .btsf import BinaryTimeSeriesFile
from .metric import Metric, MetricType

__all__ = ["to_numpy", "to_pandas"]


def to_numpy(f: BinaryTimeSeriesFile, output="structured"):
    """
    Return the data stored in a BinaryTimeSeriesFile as structured numpy.array or
    as a tuple of the columns as numpy.array, depending on the output parameter.

    f: The BinaryTimeSeriesFile instance to convert
    output: ('structured', 'columns')
    relevant numpy documentation:
        https://docs.scipy.org/doc/numpy/user/basics.rec.html
        https://docs.scipy.org/doc/numpy/reference/arrays.dtypes.html#arrays-dtypes-constructing
    """
    import numpy as np

    np_dtype_map = {
        MetricType.Double: f._byte_order + "f8",
        MetricType.Float: f._byte_order + "f4",
        MetricType.Int8: f._byte_order + "i1",
        MetricType.UInt8: f._byte_order + "u1",
        MetricType.Int16: f._byte_order + "i2",
        MetricType.UInt16: f._byte_order + "u2",
        MetricType.Int32: f._byte_order + "i4",
        MetricType.UInt32: f._byte_order + "u4",
        MetricType.Int64: f._byte_order + "i8",
        MetricType.UInt64: f._byte_order + "u8",
    }
    dt = np.dtype(
        {
            "names": tuple(m.identifier for m in f.metrics),
            "formats": tuple(np_dtype_map[m.type] for m in f.metrics),
            # "titles": tuple(f"{m.name} - {m.description}" or None for m in f.metrics),
            "itemsize": f._struct_size,
        }
    )
    f.goto_entry(entry=0)
    a = np.fromfile(f._fd, dtype=dt, offset=0)
    if output == "structured":
        return a
    if output == "columns":
        return (a[name] for name in a.dtype.names)


def to_pandas(f: BinaryTimeSeriesFile, index_metric: Union[Metric, str, int, None] = 0):
    """
    Return the data stored in a BinaryTimeSeriesFile as a pandas.DataFrame.
    The index of the DataFrame can be configured using the index_metric argument.

    f: The BinaryTimeSeriesFile instance convert.
    index_metric: The metric that should become the index column.
                  It can be specified by providing:
                      * an instance of Metric()
                      * a string representing the Metric's identifier
                      * an integer specifying the zero-based metric's index
                  By default, first metric will become the index column.
    """
    import pandas as pd

    a = to_numpy(f)
    df = pd.DataFrame.from_records(a)
    index_column_name = None
    for i, m in enumerate(f._metrics):
        if type(index_metric) is Metric and m == index_metric or \
           type(index_metric) is str and m.identifier == index_metric or \
           type(index_metric) is int and i == index_metric:
            index_column_name = m.identifier
            break
    if (index_metric is not None) and (not index_column_name):
        raise BtsfNameError("requested index metric not found in the data")
    if index_column_name:
        df.set_index(index_column_name, inplace=True)
    return df
