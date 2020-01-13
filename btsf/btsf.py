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

class HeaderID(enum.IntEnum):
    EOH = 0x0
    Main = 0x1
    Annotations = 0x2

class HeaderType(enum.IntEnum):
    NONE = 0x0
    RawBytes = 0x1
    JSON = 0x2

@attr.s
class Header():
    id = attr.ib(type=int, default=HeaderID.EOH)
    type = attr.ib(type=int, default=HeaderType.NONE)
    opt = attr.ib(type=int, default=0x0)
    data = attr.ib(type=bytes, default=attr.Factory(bytes))

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
        h_id, h_type, h_opt, h_size, = struct.unpack('<HBBL', f._fd.read(8))
        # must start with Main Header / JSON:
        assert h_id == HeaderID.Main
        assert h_type == HeaderType.JSON
        main_header = json.loads(f._fd.read(h_size).decode('utf-8'))
        # advance file pointer according to header padding
        f._fd.seek(-h_size % BinaryTimeSeriesFile.HEADER_PADDING, 1)
        # ready any further headers
        h_id, h_type, h_opt, h_size = struct.unpack('<HBBL', f._fd.read(8))
        while h_id != HeaderID.EOH:
            # One more header to read
            header = Header(id=h_id, type=h_type, opt=h_opt, data=f._fd.read(h_size))
            if h_type == HeaderType.JSON:
                header.data = json.loads(header.data.decode('utf-8'))
            f._additional_headers.append(header)
            f._fd.seek(-size % BinaryTimeSeriesFile.HEADER_PADDING, 1)
            h_code, h_opt, h_size, = struct.unpack('<HBBL', f._fd.read(8))
        f._fd.seek(-h_size % BinaryTimeSeriesFile.HEADER_PADDING, 1)

        #now interpret the main header:
        f._metrics = [Metric(**m) for m in main_header['metrics']]
        for m in f._metrics:
            m.type = Type(m.type)
        f._struct_format = main_header['struct_format']
        f._struct = struct.Struct(f._struct_format)
        f._struct_size = main_header['struct_size']
        f._byte_order = main_header['byte_order']
        f._pad_to = main_header['pad_to']
        f._data_offset = f._fd.tell()

        # round chunksize down to closest multiple of self._struct_size:
        # but self._struct_size is our minimum chunksize:
        f._chunksize = max(BinaryTimeSeriesFile._chunksize // f._struct_size * f._struct_size, f._struct_size)

        assert len(f._struct.unpack(b'\x00' * f._struct.size)) == len(f._metrics)
        assert f._struct_format == BinaryTimeSeriesFile._assemble_struct(f._byte_order, f._metrics, f._pad_to)[0]

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
    def create(filename, metrics, additional_headers=None, byte_order='<', pad_to=8):
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
        f._additional_headers = additional_headers or []

        f._fd = open(filename, 'w+b')
        f._write_main_header()
        f._write_additional_headers()
        f._write_end_of_header()
        f._data_offset = f._fd.tell()
        return f

    @property
    def metrics(self):
        return self._metrics

    def _write_additional_headers(self):
        for header in self._additional_headers:
            self._write_header(header)

    def _write_end_of_header(self):
        self._write_header(Header(id=HeaderID.EOH))

    def _write_main_header(self):
        self._fd.write(self.FILE_SIGNATURE)
        data = {
            'metrics': [m.to_dict() for m in self._metrics],
            'struct_format': self._struct_format,
            'struct_size': self._struct_size,
            'byte_order': self._byte_order,
            'pad_to': self._pad_to,
            'struct_padding': self._struct_padding,
            'file_version': 0.1,
        }
        self._write_json_header(HeaderID.Main, data=data)

    def _write_json_header(self, h_id, data=None, h_opt=0x0):
        data=json.dumps(data).encode('utf-8')
        header = Header(id=h_id, type=HeaderType.JSON, opt=h_opt, data=data)
        self._write_header(header)

    def _write_header(self, header: Header):
        h_size = len(header.data)
        self._fd.write(struct.pack('<HBBL', header.id, header.type, header.opt, h_size))
        self._fd.write(header.data)
        # any header section is padded with \x00 to a multiple of HEADER_PADDING bytes
        self._fd.write(b'\x00' * (-h_size % BinaryTimeSeriesFile.HEADER_PADDING))

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
        buf = self._fd.read(self._chunksize)
        while buf:
            offset = 0
            buf_len = len(buf)
            while offset < buf_len:
                yield self._struct.unpack_from(buf, offset=offset)
                offset += self._struct_size
            buf = self._fd.read(self._chunksize)

    def goto_entry(self, entry=0):
        assert entry < self.n_entries
        self._fd.seek(self._data_offset + entry * self._struct_size)

    def to_numpy(self, output='structured'):
        """
        output: ('structured', 'columns')
        relevant numpy documentation:
            https://docs.scipy.org/doc/numpy/user/basics.rec.html
            https://docs.scipy.org/doc/numpy/reference/arrays.dtypes.html#arrays-dtypes-constructing
        """
        import numpy as np
        np_dtype_map = {
            Type.Double: self._byte_order + 'f8',
            Type.Float:  self._byte_order + 'f4',
            Type.Int8:   self._byte_order + 'i1',
            Type.UInt8:  self._byte_order + 'u1',
            Type.Int16:  self._byte_order + 'i2',
            Type.UInt16: self._byte_order + 'u2',
            Type.Int32:  self._byte_order + 'i4',
            Type.UInt32: self._byte_order + 'u4',
            Type.Int64:  self._byte_order + 'i8',
            Type.UInt64: self._byte_order + 'u8',
        }
        dt = np.dtype({
            'names': (m.identifier for m in self.metrics),
            'formats': (np_dtype_map[m.type] for m in self.metrics),
            'titles': (f"{m.name} - {m.description}" for m in self.metrics),
            'itemsize': self._struct_size,
        })
        self.goto_entry(entry=0)
        a = np.fromfile(self._fd, dtype=dt, offset=0)
        if output == 'structured':
            return a
        if output == 'columns':
            return (a[name] for name in a.dtype.names)

    def to_pandas(self):
        import pandas as pd
        a = self.to_numpy()
        return pd.DataFrame.from_records(a)

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
