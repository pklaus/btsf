import json
import struct
from typing import List

from .exceptions import *
from .intro import *
from .metric import *

__all__ = ["BinaryTimeSeriesFile"]


class BinaryTimeSeriesFile:

    FILE_SIGNATURE = b"BinaryTimeSeriesFile_v0.1\x00\x00\x00\x00\x00\x00\x00"
    HEADER_PADDING = 8

    _chunksize = 256

    # The factory methods at the module level:
    # `create`, `openread` and `openwrite`
    # should be used to create instances of
    # this class, not __init__():
    def __init__(self, filename):
        self._fdname = filename
        self._fd = None

    @classmethod
    def openwrite(cls, filename):
        f = cls._open(filename, mode="r+b")
        f.seekend()
        return f

    @classmethod
    def openread(cls, filename):
        return cls._open(filename, mode="rb")

    @classmethod
    def _open(cls, filename, mode):
        # pylint:disable=protected-access,attribute-defined-outside-init
        f = BinaryTimeSeriesFile(filename)
        f._fd = open(filename, mode)
        if not f._fd.read(32).startswith(cls.FILE_SIGNATURE):
            raise UnknownFile("File doesn't start with btsf file signature")

        # Read all intro sections (and advance file pointer to begin of actual data...)
        f._intro_sections = []
        ish = IntroSectionHeader.load_from(f._fd)
        while ish.type != IntroSectionType.EndOfIntro:
            intro_section = IntroSection(header=ish, payload=f._fd.read(ish.payload_size))
            f._intro_sections.append(intro_section)
            # advance file pointer according to next intro section header
            f._fd.seek(ish.followup_size, 1)
            ish = IntroSectionHeader.load_from(f._fd)
        f._fd.seek(ish.followup_size, 1)

        # must start with Master Intro Section
        assert f._intro_sections[0].header.type == IntroSectionType.MasterIntro
        master_intro = json.loads(f._intro_sections[0].payload.decode("utf-8"))

        # now interpret the master intro:
        f._metrics = [Metric(**m) for m in master_intro["metrics"]]
        for m in f._metrics:
            m.type = MetricType(m.type)
        f._struct_format = master_intro["struct_format"]
        f._struct = struct.Struct(f._struct_format)
        f._struct_size = master_intro["struct_size"]
        f._byte_order = master_intro["byte_order"]
        f._pad_to = master_intro["pad_to"]
        f._data_offset = f._fd.tell()

        # round chunksize down to closest multiple of f._struct_size:
        # but f._struct_size is our minimum chunksize:
        f._chunksize = max(
            cls._chunksize // f._struct_size * f._struct_size, f._struct_size
        )

        assert len(f._struct.unpack(b"\x00" * f._struct.size)) == len(f._metrics)
        assert (
            f._struct_format
            == cls._assemble_struct(f._byte_order, f._metrics, f._pad_to)[0]
        )

        return f

    @staticmethod
    def _assemble_struct(byte_order, metrics, pad_to=None):
        struct_format = byte_order + "".join(m.type.value for m in metrics)
        if pad_to:
            size = struct.calcsize(struct_format)
            struct_padding = -size % pad_to
            struct_format += "%dx" % struct_padding
        return struct_format, struct_padding

    @property
    def _struct_padding(self):
        return self._assemble_struct(self._byte_order, self._metrics, self._pad_to)[1]

    def seekend(self):
        self._fd.seek(0, 2)  # SEEK_END

    @classmethod
    def _validate_intro_section(cls, intro_section, pad_to):
        if intro_section.header.total_size % pad_to:
            raise InvalidIntroSection("size not aligned to %i bytes" % pad_to)

    @classmethod
    def create(
        cls,
        filename: str,
        metrics: List[Metric],
        intro_sections: List[IntroSection] = None,
        byte_order: str = "<",
        pad_to: int = 8,
    ):
        # pylint:disable=protected-access

        if intro_sections:
            for intro_section in intro_sections:
                cls._validate_intro_section(intro_section, pad_to)

        struct_format, _ = cls._assemble_struct(byte_order, metrics, pad_to)

        f = BinaryTimeSeriesFile(filename)

        f._metrics = metrics
        f._struct_format = struct_format
        f._struct = struct.Struct(struct_format)
        f._struct_size = f._struct.size
        f._byte_order = byte_order
        f._pad_to = pad_to
        f._intro_sections = []
        f._populate_master_intro_section()
        f._intro_sections += intro_sections or []
        f._chunksize = max(
            cls._chunksize // f._struct_size * f._struct_size, f._struct_size
        )

        f._fd = open(filename, "w+b")
        f._write_file_signature()
        f._write_all_intro_sections()
        f._write_end_of_intro()
        f._data_offset = f._fd.tell()
        return f

    @property
    def metrics(self):
        return self._metrics

    def _write_file_signature(self):
        self._fd.write(self.FILE_SIGNATURE)

    def _populate_master_intro_section(self):
        data = {
            "metrics": [m.to_dict() for m in self._metrics],
            "struct_format": self._struct_format,
            "struct_size": self._struct_size,
            "byte_order": self._byte_order,
            "pad_to": self._pad_to,
            "struct_padding": self._struct_padding,
            "file_version": 0.1,
        }
        payload = json.dumps(data).encode("utf-8")
        ish = IntroSectionHeader(
            type=IntroSectionType.MasterIntro,
            payload_size=len(payload),
            followup_size=-len(payload) % self.HEADER_PADDING,
        )
        intro_section = IntroSection(header=ish, payload=payload)
        self._intro_sections.append(intro_section)

    def _write_single_intro_section(self, intro_section: IntroSection):
        self._fd.write(intro_section.header.pack())
        self._fd.write(intro_section.payload)
        self._fd.write(b"\x00" * intro_section.header.followup_size)

    def _write_all_intro_sections(self):
        for intro_section in self._intro_sections:
            self._write_single_intro_section(intro_section)

    def _write_end_of_intro(self):
        self._write_single_intro_section(
            IntroSection(IntroSectionHeader(type=IntroSectionType.EndOfIntro))
        )

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
        self._fd.seek(-self._struct_size, 2)  # SEEK_END
        return next(self)

    def __next__(self):
        data = self._fd.read(self._struct_size)
        if len(data) == 0:
            raise NoFurtherData()  # which also is a StopIteration
        return self._struct.unpack(data)

    def __getitem__(self, i):
        if i < 0:
            i += self.n_entries
        if 0 <= i < self.n_entries:
            self.goto_entry(entry=i)
            return next(self)
        raise IndexError("Index i={} out of range ({})".format(i, range(self.n_entries)))

    def __len__(self):
        return self.n_entries

    def __iter__(self):
        """
        A generator facilitating iterating over all entry tuples.
        """
        self.goto_entry(entry=0)
        # naive approach (slower than the one following)
        # buf = self._fd.read(self._struct_size)
        # while len(buf) == self._struct_size:
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



    @property
    def n_entries(self):
        current_pos = self._fd.tell()
        start = self._data_offset
        self.seekend()
        end = self._fd.tell()
        self._fd.seek(current_pos)
        n_data_bytes = end - start

        if n_data_bytes % self._struct_size != 0:
            raise InvalidFileContent(
                f"{n_data_bytes % self._struct_size} trailing bytes at the end of the file"
            )
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
