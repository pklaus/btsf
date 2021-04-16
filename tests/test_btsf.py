from pytest import raises, approx as pytest_approx

import math
import tempfile
import io

from btsf import BinaryTimeSeriesFile, Metric, MetricType
from btsf import IntroSection, IntroSectionHeader, IntroSectionType
from btsf import InvalidIntroSection


def approx(*args, nan_ok=True, **kwargs):
    """ custom variant of pytest.approx with nan_ok=True as default """
    # Idea: change this custom variant to make it symmetric regarding the
    # relative comparison...
    return pytest_approx(*args, nan_ok=nan_ok, **kwargs)


TYPICAL_METRICS = [
    Metric("time", MetricType.Double),
    Metric("power", MetricType.Float),
    Metric("counter", MetricType.UInt64),
    Metric("flags", MetricType.UInt8),
]

# fmt: off
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
# fmt: on


def test_append_invalid_values():

    # value too large to be represented as IEEE-754 32-bit floating point
    with tempfile.NamedTemporaryFile(suffix=".btsf") as tf:
        metrics = [Metric("some_float", MetricType.Float)]
        with BinaryTimeSeriesFile.create(tf.name, metrics) as f:
            with raises(OverflowError):
                f.append(9.9e200)

    # value too large to be represented as IEEE-754 64-bit floating point
    value = 200e200000000
    assert value == float("inf")
    with tempfile.NamedTemporaryFile(suffix=".btsf") as tf:
        metrics = [Metric("some_double", MetricType.Double)]
        with BinaryTimeSeriesFile.create(tf.name, metrics) as f:
            f.append(value)
            assert value == f.last()[0]

    # NaN in IEEE-754 32-bit floating point
    value = float("nan")
    with tempfile.NamedTemporaryFile(suffix=".btsf") as tf:
        metrics = [Metric("some_double", MetricType.Double)]
        with BinaryTimeSeriesFile.create(tf.name, metrics) as f:
            f.append(value)
            assert math.isnan(f.last()[0])


def test_write_then_read():

    tf = tempfile.NamedTemporaryFile(suffix=".btsf")

    with BinaryTimeSeriesFile.create(tf.name, TYPICAL_METRICS) as f:
        for t in VALID_TUPLES:
            f.append(*t)
        assert f.n_entries == len(VALID_TUPLES)

        # check our implementation of __iter__()
        assert len([t for t in f]) == len(VALID_TUPLES)
        # twice...
        assert len([t for t in f]) == len(VALID_TUPLES)

        # check our implementation of __len__()
        assert len(f) == len(VALID_TUPLES)

    # open the file again for reading only:
    with BinaryTimeSeriesFile.openread(tf.name) as f:
        # test if the file can be read back with its fundamental attributes
        assert f._byte_order == "<"
        assert f._struct_size == 24
        assert f._struct_format == "<dfQB3x"
        assert len(f._metrics) == 4

        # check for goto_entry()
        f.goto_entry(2)

        # check for __iter__()
        for i, values in enumerate(f):
            assert VALID_TUPLES[i] == approx(values)

        # check for __getitem__():
        for i, t in enumerate(VALID_TUPLES):
            assert t == approx(f[i])

        # check we actually read the last value in our file
        # using the __next__() method under the hood:
        with raises(StopIteration):
            next(f)

        # file was opened for reading only
        with raises(io.UnsupportedOperation):
            f.append(*VALID_TUPLES[0])

    # open the file again for appending (and reading)
    with BinaryTimeSeriesFile.openwrite(tf.name) as f:
        assert f._metrics == TYPICAL_METRICS

        # append all data points again:
        for t in VALID_TUPLES:
            f.append(*t)

    with BinaryTimeSeriesFile.openread(tf.name) as f:
        for i, values in enumerate(f):
            assert VALID_TUPLES[i % len(VALID_TUPLES)] == approx(values)
        with raises(StopIteration):
            next(f)


def test_write_and_read_on_same_instance():

    tf = tempfile.NamedTemporaryFile(suffix=".btsf")

    with BinaryTimeSeriesFile.create(tf.name, TYPICAL_METRICS) as f:

        # test proper creation and fundamental attributes
        assert f._byte_order == "<"
        assert f._struct_size == 24
        assert f._struct_format == "<dfQB3x"
        assert len(f._metrics) == 4

        # test .n_entries when value != 0
        assert f.n_entries == 0

        for t in VALID_TUPLES:
            f.append(*t)

        # test .n_entries when value != 0
        assert f.n_entries == len(VALID_TUPLES)

        # test .goto_entry() 2nd position and read the following two entries:
        f.goto_entry(entry=1)
        assert VALID_TUPLES[1] == approx(next(f))
        assert VALID_TUPLES[2] == approx(next(f))

        # test reading back the full file:
        for i, values in enumerate(f):
            assert VALID_TUPLES[i] == approx(values)

        with raises(StopIteration):
            next(f)

        # test first() and last()
        assert VALID_TUPLES[0] == approx(f.first())
        assert VALID_TUPLES[-1] == approx(f.last())


def test_invalid_further_intro():
    tf = tempfile.NamedTemporaryFile(suffix=".btsf")

    payload = b""
    non_aligned_intro = IntroSection(
        header=IntroSectionHeader(
            type=IntroSectionType.GenericBinary,
            payload_size=len(payload),
            followup_size=3,
        ),
        payload=payload,
    )
    with raises(InvalidIntroSection):
        f = BinaryTimeSeriesFile.create(
            tf.name, TYPICAL_METRICS, intro_sections=[non_aligned_intro]
        )


def test_write_further_intro():

    tf = tempfile.NamedTemporaryFile(suffix=".btsf")

    annotations = {}
    import json

    payload = json.dumps(annotations).encode("utf-8")
    annotation_intro = IntroSection(
        header=IntroSectionHeader(
            type=IntroSectionType.Annotations,
            payload_size=len(payload),
            followup_size=-len(payload) % 8,
        ),
        payload=payload,
    )
    further_intro_sections = [annotation_intro]
    with BinaryTimeSeriesFile.create(
        tf.name, TYPICAL_METRICS, intro_sections=further_intro_sections, pad_to=8
    ) as f:
        for t in VALID_TUPLES:
            f.append(*t)
        assert f.n_entries == len(VALID_TUPLES)

        # check our implementation of __iter__()
        assert len([t for t in f]) == len(VALID_TUPLES)
        # twice...
        assert len([t for t in f]) == len(VALID_TUPLES)

        # check our implementation of __len__()
        assert len(f) == len(VALID_TUPLES)

    # open the file again for reading only:
    with BinaryTimeSeriesFile.openread(tf.name) as f:
        # test if the file can be read back with its fundamental attributes
        assert f._byte_order == "<"
        assert annotation_intro == f._intro_sections[1]
        assert f._struct_size == 24
        assert f._struct_format == "<dfQB3x"
        assert len(f._metrics) == 4

        # check for goto_entry()
        f.goto_entry(2)

        # check for __iter__()
        for i, values in enumerate(f):
            assert VALID_TUPLES[i] == approx(values)

        # check for __getitem__():
        for i, t in enumerate(VALID_TUPLES):
            assert t == approx(f[i])

        # check we actually read the last value in our file
        # using the __next__() method under the hood:
        with raises(StopIteration):
            next(f)

        # file was opened for reading only
        with raises(io.UnsupportedOperation):
            f.append(*VALID_TUPLES[0])
