#!/usr/bin/env python

import enum
import json
import struct
import attr

class Type(enum.Enum):
    Float = 'f'
    Double = 'd'
    Int8 = 'b'
    UInt8 = 'B'
    Int16 = 'h'
    UInt16 = 'H'
    Int32 = 'l'
    UInt32 = 'L'
    Int64 = 'q'
    UInt64 = 'Q'

@attr.s
class Metric():
    identifier = attr.ib()
    type = attr.ib(type=Type)
    name = attr.ib(default='', type=str)
    unit = attr.ib(default='', type=str)
    description = attr.ib(default='', type=str)
    is_time = attr.ib(default=False, type=bool)

    def to_dict(self):
        d = attr.asdict(self)
        d['type'] = self.type.value
        return d
        #return {
        #    'identifier': self.identifier,
        #    'type': self.type.value,
        #    'name': self.name,
        #    'unit': self.unit,
        #    'description': self.description,
        #    'is_time': self.is_time,
        #}

class BinaryTimeSeriesFile():

    FILE_SIGNATURE = b'BinaryTimeSeriesFile_v0.1\x00\x00\x00\x00\x00\x00\x00'

    def __init__(self, filename):
        self.filename = filename
        self.file = None

    @staticmethod
    def openwrite(f):
        return BinaryTimeSeriesFile._open(f, mode='r+b')

    @staticmethod
    def openread(f):
        return BinaryTimeSeriesFile._open(f, mode='rb')

    @staticmethod
    def _open(f, mode):
        btsf = open(f, mode)
        btsf._attachwritemethod()
        btsf.seekend()
        return btsf

    def seekend(self):
        self.file.seek(0, 2)    # SEEK_END

    @staticmethod
    def create(filename, metrics, byte_order='<', pad_to=8):
        btsf = BinaryTimeSeriesFile(filename)
        btsf.file = open(filename, 'wb')
        btsf.metrics = metrics
        btsf.byte_order = byte_order
        btsf.struct_format = byte_order + ''.join(m.type.value for m in metrics)
        if pad_to:
            size = struct.calcsize(btsf.struct_format)
            n_padding_bytes = -size % pad_to
            btsf.struct_format += '%dx' % n_padding_bytes
        btsf.struct_size = struct.calcsize(btsf.struct_format)
        btsf._write_header()
        return btsf

    def _write_header(self):
        self.file.write(self.FILE_SIGNATURE)
        header = json.dumps({
            'metrics': [m.to_dict() for m in self.metrics],
            'struct_format': self.struct_format,
            'struct_size': self.struct_size,
            'file_version': 0.1,
        })
        header = header.encode('utf-8')
        self.file.write(struct.pack(self.byte_order + 'Q', len(header)))
        self.file.write(header)

    def log_new_samples(self, *values):
        self.file.write(struct.pack(self.struct_format, *values))

    def flush(self):
        self.file.flush()

    def close(self):
        self.file.close()

    # context manager protocol
    def __enter__(self):
        return self

    def __exit__(self, type_, value, tb):
        self.close()
