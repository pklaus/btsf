from unittest import TestCase

from btsf import BinaryTimeSeriesFile, Metric, Type

class TestBinaryTimeSeriesFile(TestCase):
    def test_write_read(self):
        metrics = [
            Metric('time', Type.Double),
            Metric('power', Type.Float),
            Metric('counter', Type.UInt64),
            Metric('flags', Type.UInt8),
        ]

        tuple_1 = (1.1, 2.2, 0xf0f0f0f0f0f0f0f0, 1)
        tuple_2 = (3.3, 4.4, 0xffffffffffffffff, 2)
        tuple_3 = (5.0, 1.0, 0x123456789ABCDEF1, 3)
        with BinaryTimeSeriesFile.create('test.btsf', metrics) as f:
            f.log_new_samples(*tuple_1)
            f.log_new_samples(*tuple_2)
            f.log_new_samples(*tuple_3)

        with BinaryTimeSeriesFile.openread('test.btsf') as f:
            self.assertEqual(f._byte_order, '<')
            self.assertEqual(f._struct_size, 24)
            self.assertEqual(f._struct_format, '<dfQB3x')
            self.assertEqual(len(f._metrics), 4)
            for wrote, got in zip(tuple_1, f.read()):
                self.assertAlmostEqual(wrote, got, places=5)
            for wrote, got in zip(tuple_2, f.read()):
                self.assertAlmostEqual(wrote, got, places=5)
            for wrote, got in zip(tuple_3, f.read()):
                self.assertAlmostEqual(wrote, got, places=5)
            self.assertRaises(EOFError, f.read)
