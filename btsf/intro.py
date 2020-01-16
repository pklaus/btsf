import attr
import enum
import io
import struct

@attr.s
class IntroSectionHeader():

    STRUCT = struct.Struct('<B7xLL')

    class Kind(enum.IntEnum):
        EndOfIntro = 0x0
        MasterIntroSection = 0x1
        AnnotationsSection = 0x2

    kind = attr.ib(type=int, default=Kind.EndOfIntro)
    payload_size = attr.ib(type=int, default=0)
    followup_size = attr.ib(type=int, default=0)

    def pack(self) -> bytes:
        return self.STRUCT.pack(self.kind, self.payload_size, self.followup_size)

    @staticmethod
    def load_from(fd: io.IOBase):
        data = fd.read(IntroSectionHeader.STRUCT.size)
        kind, payload_size, followup_size = IntroSectionHeader.STRUCT.unpack(data)
        return IntroSectionHeader(kind, payload_size, followup_size)

@attr.s
class IntroSection():
    header = attr.ib(type=IntroSectionHeader)
    payload = attr.ib(type=bytes, default=b'')