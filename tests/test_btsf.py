from unittest import TestCase
import tempfile

from btsf import BinaryTimeSeriesFile, Metric, Type

class TestBinaryTimeSeriesFile(TestCase):
    def test_write_read(self):

        tf = tempfile.NamedTemporaryFile(suffix='.btsf')

        metrics = [
            Metric('time', Type.Double),
            Metric('power', Type.Float),
            Metric('counter', Type.UInt64),
            Metric('flags', Type.UInt8),
        ]

        tuple_1 = (1.1, 2.2, 0xf0f0f0f0f0f0f0f0, 1)
        tuple_2 = (3.3, 4.4, 0xffffffffffffffff, 2)
        tuple_3 = (5.0, 1.0, 0x123456789ABCDEF1, 3)
        with BinaryTimeSeriesFile.create(tf.name, metrics) as f:
            f.append(*tuple_1)
            f.append(*tuple_2)
            f.append(*tuple_3)

        with BinaryTimeSeriesFile.openread(tf.name) as f:
            self.assertEqual(f._byte_order, '<')
            self.assertEqual(f._struct_size, 24)
            self.assertEqual(f._struct_format, '<dfQB3x')
            self.assertEqual(len(f._metrics), 4)
            for wrote, got in zip(tuple_1, next(f)):
                self.assertAlmostEqual(wrote, got, places=5)
            for wrote, got in zip(tuple_2, next(f)):
                self.assertAlmostEqual(wrote, got, places=5)
            for wrote, got in zip(tuple_3, next(f)):
                self.assertAlmostEqual(wrote, got, places=5)
            self.assertRaises(StopIteration, lambda: next(f))


        tuple_4 = (4.4, 44.4, 0x4444444444444444, 0xb4)
        tuple_5 = (5.5, 55.5, 0x5555555555555555, 0xb5)
        tuple_6 = (6.6, 66.6, 0x6666666666666666, 0xb6)
        with BinaryTimeSeriesFile.openwrite(tf.name) as f:
            self.assertEqual(f._metrics, metrics)
            f.append(*tuple_4)
            f.append(*tuple_5)
            f.append(*tuple_6)

        with BinaryTimeSeriesFile.openread(tf.name) as f:
            self.assertEqual(f._byte_order, '<')
            self.assertEqual(f._struct_size, 24)
            self.assertEqual(f._struct_format, '<dfQB3x')
            self.assertEqual(len(f._metrics), 4)
            for wrote, got in zip(tuple_1, next(f)):
                self.assertAlmostEqual(wrote, got, places=5)
            for wrote, got in zip(tuple_2, next(f)):
                self.assertAlmostEqual(wrote, got, places=5)
            for wrote, got in zip(tuple_3, next(f)):
                self.assertAlmostEqual(wrote, got, places=5)
            for wrote, got in zip(tuple_4, next(f)):
                self.assertAlmostEqual(wrote, got, places=5)
            for wrote, got in zip(tuple_5, next(f)):
                self.assertAlmostEqual(wrote, got, places=5)
            for wrote, got in zip(tuple_6, next(f)):
                self.assertAlmostEqual(wrote, got, places=5)
            self.assertRaises(StopIteration, lambda: next(f))
