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
    HEADER_PADDING = 8

    # the factory methods at the module level, `create`, `openread` and `openwrite` should be used to create instances of this class.
    def __init__(self, filename):
        self._fdname = filename
        self._fd = None

    @staticmethod
    def openwrite(filename):
        f = BinaryTimeSeriesFile._open(filename, mode='r+b')
        f.seekend()
        return f

    @staticmethod
    def openread(filename):
        return BinaryTimeSeriesFile._open(filename, mode='rb')

    @staticmethod
    def _open(filename, mode):
        f = BinaryTimeSeriesFile(filename)
        f._fd = open(filename, mode)
        if not f._fd.read(32).startswith(BinaryTimeSeriesFile.FILE_SIGNATURE):
            raise UnknownFileError("File doesn't start with btsf file signature")
        size, = struct.unpack('<Q', f._fd.read(8))
        header = json.loads(f._fd.read(size).decode('utf-8'))
        f._fd.seek(-size % BinaryTimeSeriesFile.HEADER_PADDING, 1)
        #size, = struct.unpack('<Q', f._fd.read(8))
        #annotations = json.load(f._fd.read(size).decode('utf-8'))
        #f._fd.seek((-size % BinaryTimeSeriesFile.HEADER_PADDING, 1)
        metrics = [Metric(**m) for m in header['metrics']]
        for m in metrics:
            m.type = Type(m.type)

        f._metrics = metrics
        f._struct_format = header['struct_format']
        f._byte_order = header['byte_order']
        f._pad_to = header['pad_to']
        f._struct_size = header['struct_size']
        f._data_offset = f._fd.tell()

        return f

    def seekend(self):
        self._fd.seek(0, 2)    # SEEK_END

    @staticmethod
    def create(filename, metrics, byte_order='<', pad_to=8):
        struct_format = byte_order + ''.join(m.type.value for m in metrics)
        if pad_to:
            size = struct.calcsize(struct_format)
            struct_format += '%dx' % (-size % pad_to)

        f = BinaryTimeSeriesFile(filename)

        f._metrics = metrics
        f._struct_format = struct_format
        f._byte_order = byte_order
        f._pad_to = pad_to
        f._struct_size = struct.calcsize(struct_format)

        f._fd = open(filename, 'wb')
        f._write_header()
        f._data_offset = f._fd.tell()
        return f

    @property
    def metrics(self):
        return self._metrics

    def _write_header(self):
        self._fd.write(self.FILE_SIGNATURE)
        header = json.dumps({
            'metrics': [m.to_dict() for m in self._metrics],
            'struct_format': self._struct_format,
            'byte_order': self._byte_order,
            'pad_to': self._pad_to,
            'struct_size': self._struct_size,
            'file_version': 0.1,
        })
        header = header.encode('utf-8')
        self._fd.write(struct.pack('<Q', len(header)))
        self._fd.write(header)
        self._fd.write(b'\x00' * (-len(header) % BinaryTimeSeriesFile.HEADER_PADDING))

    def log_new_samples(self, *values):
        self._fd.write(struct.pack(self._struct_format, *values))

    def read_last(self):
        if self.n_entries == 0:
            raise BtsfEOFError()
        self._fd.seek(-self._struct_size, 2)    # SEEK_END
        return self.read()

    def read(self):
        data = self._fd.read(self._struct_size)
        if len(data) == 0:
            raise BtsfEOFError()
        return struct.unpack(self._struct_format, data)

    def iter_entries(self):
        """
        A generator facilitating iterating over all entry tuples.
        """
        data = self._fd.read(self._struct_size)
        while len(data) == self._struct_size:
            yield struct.unpack(self._struct_format, data)
            data = self._fd.read(self._struct_size)

    def goto_entry(self, entry=0):
        assert entry < self.n_entries
        self._fd.seek(self._data_offset + entry * self._struct_size)

    @property
    def n_entries(self):
        current_pos = self._fd.tell()
        start = self._data_offset
        self.seekend()
        end = self._fd.tell()
        self._fd.seek(current_pos)
        n_data_bytes = end - start

        if n_data_bytes % self._struct_size != 0:
            raise InvalidFileContentError(f'{n_data_bytes % self._struct_size} trailing bytes at the end of the file')
        return n_data_bytes // self._struct_size

    def flush(self):
        self._fd.flush()

    def close(self):
        self._fd.close()

    # context manager protocol
    def __enter__(self):
        return self

    def __exit__(self, type_, value, tb):
        self.close()

class BtsfError(Exception):
    pass

class UnknownFileError(NameError, BtsfError):
    pass

class BtsfEOFError(EOFError, BtsfError):
    pass

class InvalidFileContentError(NameError, BtsfError):
    pass
