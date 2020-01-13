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

    _chunksize = 256

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
        f._struct = struct.Struct(f._struct_format)
        f._struct_size = header['struct_size']
        f._byte_order = header['byte_order']
        f._pad_to = header['pad_to']
        f._data_offset = f._fd.tell()
        # round chunksize down to closest multiple of self._struct_size:
        # but self._struct_size is our minimum chunksize:
        f._chunksize = max(BinaryTimeSeriesFile._chunksize // f._struct_size * f._struct_size, f._struct_size)

        assert f._struct_format == BinaryTimeSeriesFile._assemble_struct(f._byte_order, metrics, f._pad_to)[0]

        return f

    @staticmethod
    def _assemble_struct(byte_order, metrics, pad_to=None):
        struct_format = byte_order + ''.join(m.type.value for m in metrics)
        if pad_to:
            size = struct.calcsize(struct_format)
            struct_padding = -size % pad_to
            struct_format += '%dx' % struct_padding
        return struct_format, struct_padding

    @property
    def _struct_padding(self):
        return BinaryTimeSeriesFile._assemble_struct(
            self._byte_order,
            self._metrics,
            self._pad_to)[1]

    def seekend(self):
        self._fd.seek(0, 2)    # SEEK_END

    @staticmethod
    def create(filename, metrics, byte_order='<', pad_to=8):
        struct_format, struct_padding = BinaryTimeSeriesFile._assemble_struct(
            byte_order, metrics, pad_to)

        f = BinaryTimeSeriesFile(filename)

        f._metrics = metrics
        f._struct_format = struct_format
        f._struct = struct.Struct(struct_format)
        f._struct_size = f._struct.size
        f._byte_order = byte_order
        f._pad_to = pad_to
        f._chunksize = max(BinaryTimeSeriesFile._chunksize // f._struct_size * f._struct_size, f._struct_size)

        f._fd = open(filename, 'w+b')
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
            'struct_size': self._struct_size,
            'byte_order': self._byte_order,
            'pad_to': self._pad_to,
            'struct_padding': self._struct_padding,
            'file_version': 0.1,
        })
        header = header.encode('utf-8')
        self._fd.write(struct.pack('<Q', len(header)))
        self._fd.write(header)
        self._fd.write(b'\x00' * (-len(header) % BinaryTimeSeriesFile.HEADER_PADDING))

    def append(self, *values):
        self.seekend()
        self._fd.write(struct.pack(self._struct_format, *values))

    def first(self):
        if self.n_entries == 0:
            raise EmptyBtsfError()
        self._fd.seek(self._data_offset)
        return next(self)

    def last(self):
        if self.n_entries == 0:
            raise EmptyBtsfError()
        self._fd.seek(-self._struct_size, 2)    # SEEK_END
        return next(self)

    def __next__(self):
        data = self._fd.read(self._struct_size)
        if len(data) == 0:
            raise NoFurtherData() # which also is a StopIteration
        return self._struct.unpack(data)

    def __getitem__(self, i):
        if i < 0:
            i += self.n_entries
        if 0 <= i < self.n_entries:
            self.goto_entry(entry=i)
            return next(self)
        raise IndexError('Index i={} out of range ({})'.format(i, range(self.n_entries)))

    def __len__(self):
        return self.n_entries

    def __iter__(self):
        """
        A generator facilitating iterating over all entry tuples.
        """
        self.goto_entry(entry=0)
        # naive approach (slower than the one following)
        #buf = self._fd.read(self._struct_size)
        #while len(buf) == self._struct_size:
        #    yield self._struct.unpack(buf)
        #    buf = self._fd.read(self._struct_size)
        buf = self._fd.read(chunksize)
        while buf:
            offset = 0
            buf_len = len(buf)
            while offset < buf_len:
                yield self._struct.unpack_from(buf, offset=offset)
                offset += self._struct_size
            buf = self._fd.read(chunksize)

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

class NoFurtherData(StopIteration, BtsfError):
    pass

class EmtpyBtsfError(BtsfError):
    pass

class InvalidFileContentError(NameError, BtsfError):
    pass
