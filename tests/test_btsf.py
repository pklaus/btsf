from unittest import TestCase
from unittest.util import safe_repr
import math
import tempfile
import io

from btsf import BinaryTimeSeriesFile, Metric, Type

DEFAULT_METRICS = [
    Metric('time', Type.Double),
    Metric('power', Type.Float),
    Metric('counter', Type.UInt64),
    Metric('flags', Type.UInt8),
]

VALID_TUPLES = [
    # simple / straightforward examples:
    (     1.1,         2.2,         0xf0f0f0f0f0f0f0f0,          1),
    (     3.3,         4.4,         0xffffffffffffffff,          2),
    (     5.0,         1.0,         0x123456789ABCDEF1,          3),
    (     4.4,        44.4,         0x4444444444444444,       0xb4),
    (     5.5,        55.5,         0x5555555555555555,       0xb5),
    (     6.6,        66.6,         0x6666666666666666,       0xb6),
    (111111.00000001,  2.3874e-13, 0xdeadbeafdeadbeaf,      0b010),
    (333333.00000003,  3.4575e+22, 0x7878787878787878,      0b101),
    # special IEEE-754 values representable: nan nan
    (float('nan'), float('nan'), 0, 0),
    # special IEEE-754 values representable: +inf -inf
    (float('+inf'), float('-inf'), 0, 0),
    # special IEEE-754 values representable: -inf +inf
    (float('-inf'), float('inf'), 0, 0),
    # special IEEE-754 values: -0.0 -0.0
    (-0.0, -0.0, 0, 0),
    # smallest positive values representable:
    (2.2250738585072014e-103, 1.4012984643e-45, 0x0000000000000000, 0b00000000),
    # largest values representable:
    ( 1.7976931348623157e+308, 3.4028234664e38, 0xffffffffffffffff, 0b11111111),
    # double with 1010...      float with 00110011.. UInt64 obvious      Uint8 obvious
    (-3.7206620809969885e-103, 4.17232506322307e-08, 0x1111111111111111, 0b10001000),
]

class TestBinaryTimeSeriesFile(TestCase):

    def test_append_invalid_values(self):

        # value too large to be represented as IEEE-754 32-bit floating point
        with tempfile.NamedTemporaryFile(suffix='.btsf') as tf:
            metrics = [Metric('some_float', Type.Float)]
            with BinaryTimeSeriesFile.create(tf.name, metrics) as f:
                self.assertRaises(OverflowError, f.append, 9.9e200)

        # value too large to be represented as IEEE-754 64-bit floating point
        value = 200e200000000
        self.assertEqual(value, float('inf'))
        with tempfile.NamedTemporaryFile(suffix='.btsf') as tf:
            metrics = [Metric('some_double', Type.Double)]
            with BinaryTimeSeriesFile.create(tf.name, metrics) as f:
                f.append(value)
                self.assertEqual(value, f.last()[0])

        # NaN in IEEE-754 32-bit floating point
        value = float('nan')
        self.assertIsNaN(value)
        with tempfile.NamedTemporaryFile(suffix='.btsf') as tf:
            metrics = [Metric('some_double', Type.Double)]
            with BinaryTimeSeriesFile.create(tf.name, metrics) as f:
                f.append(value)
                self.assertIsNaN(f.last()[0])

    def test_write_then_read(self):

        tf = tempfile.NamedTemporaryFile(suffix='.btsf')

        with BinaryTimeSeriesFile.create(tf.name, DEFAULT_METRICS) as f:
            for t in VALID_TUPLES:
                f.append(*t)
            self.assertEqual(f.n_entries, len(VALID_TUPLES))

            # check our implementation of __iter__()
            self.assertEqual(len([t for t in f]), len(VALID_TUPLES))
            # twice...
            self.assertEqual(len([t for t in f]), len(VALID_TUPLES))

            # check our implementation of __len__()
            self.assertEqual(len(f), len(VALID_TUPLES))

        # open the file again for reading only:
        with BinaryTimeSeriesFile.openread(tf.name) as f:
            # test if the file can be read back with its fundamental attributes
            self.assertEqual(f._byte_order, '<')
            self.assertEqual(f._struct_size, 24)
            self.assertEqual(f._struct_format, '<dfQB3x')
            self.assertEqual(len(f._metrics), 4)

            # check for goto_entry()
            f.goto_entry(2)

            # check for __iter__()
            for i, values in enumerate(f):
                for written_val, read_val in zip(VALID_TUPLES[i], values):
                    self.assertFloatAlmostEqual(written_val, read_val)

            # check for __getitem__():
            for i, t in enumerate(VALID_TUPLES):
                for written_val, read_val in zip(t, f[i]):
                    self.assertFloatAlmostEqual(written_val, read_val)

            # check we actually read the last value in our file
            # using the __next__() method under the hood:
            self.assertRaises(StopIteration, lambda: next(f))

            # file was opened for reading only
            self.assertRaises(io.UnsupportedOperation, f.append, *VALID_TUPLES[0])

        # open the file again for appending (and reading)
        with BinaryTimeSeriesFile.openwrite(tf.name) as f:
            self.assertEqual(f._metrics, DEFAULT_METRICS)

            # append all data points again:
            for t in VALID_TUPLES:
                f.append(*t)

        with BinaryTimeSeriesFile.openread(tf.name) as f:
            for i, values in enumerate(f):
                for written_val, read_val in zip(VALID_TUPLES[i % len(VALID_TUPLES)], values):
                    self.assertFloatAlmostEqual(written_val, read_val)
            self.assertRaises(StopIteration, lambda: next(f))

    def test_write_and_read_on_same_instance(self):

        tf = tempfile.NamedTemporaryFile(suffix='.btsf')

        with BinaryTimeSeriesFile.create(tf.name, DEFAULT_METRICS) as f:

            # test proper creation and fundamental attributes
            self.assertEqual(f._byte_order, '<')
            self.assertEqual(f._struct_size, 24)
            self.assertEqual(f._struct_format, '<dfQB3x')
            self.assertEqual(len(f._metrics), 4)

            # test .n_entries when value != 0
            self.assertEqual(f.n_entries, 0)

            for t in VALID_TUPLES:
                f.append(*t)

            # test .n_entries when value != 0
            self.assertEqual(f.n_entries, len(VALID_TUPLES))

            # test .goto_entry() 2nd position and read the following two entries:
            f.goto_entry(entry=1)
            for wrote, got in zip(VALID_TUPLES[1], next(f)):
                self.assertFloatAlmostEqual(wrote, got)
            for wrote, got in zip(VALID_TUPLES[2], next(f)):
                self.assertFloatAlmostEqual(wrote, got)

            # test reading back the full file:
            for i, values in enumerate(f):
                for written_val, read_val in zip(VALID_TUPLES[i], values):
                    self.assertFloatAlmostEqual(wrote, got)

            self.assertRaises(StopIteration, lambda: next(f))

            # test first() and last()
            for wrote, got in zip(VALID_TUPLES[0], f.first()):
                self.assertFloatAlmostEqual(wrote, got)

            for wrote, got in zip(VALID_TUPLES[-1], f.last()):
                self.assertFloatAlmostEqual(wrote, got)

    def assertIsNaN(self, value, msg=None):
        """
        Fail if provided value is not NaN
        """
        standardMsg = "%s is not NaN" % str(value)
        try:
            if not math.isnan(value):
                self.fail(self._formatMessage(msg, standardMsg))
        except:
            self.fail(self._formatMessage(msg, standardMsg))

    def assertFloatAlmostEqual(self, first, second, allowed_rel_dev=5e-8, msg=None):
        """
        allowed_rel_dev: relative deviation of the two from their arithmetic mean
        """
        if first == second:
            return
        if type(first) is float and type(second) is float:
            if math.isnan(first) and math.isnan(second):
                return
            rel_dev = abs(first - second) *2 / (first + second)
            #rel_dev = abs(first/second - 1) # this one would be sensitive to swapping first and second
            if rel_dev <= allowed_rel_dev:
                return
            else:
                standardMsg = '%s != %s within %s relative deviation (%s deviation)' % (
                    safe_repr(first),
                    safe_repr(second),
                    safe_repr(allowed_rel_dev),
                    safe_repr(rel_dev))
                self.fail(self._formatMessage(msg, standardMsg))
