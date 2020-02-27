import attr
import enum
import io
import struct

__all__ = ["IntroSectionHeader", "IntroSection", "IntroSectionType"]

class IntroSectionType(enum.IntEnum):
    EndOfIntro = 0x0
    MasterIntroSection = 0x1
    AnnotationsSection = 0x2

@attr.s
class IntroSectionHeader():

    STRUCT = struct.Struct('<B7xLL')

    type = attr.ib(type=int, default=IntroSectionType.EndOfIntro)
    payload_size = attr.ib(type=int, default=0)
    followup_size = attr.ib(type=int, default=0)

    def pack(self) -> bytes:
        return self.STRUCT.pack(self.type, self.payload_size, self.followup_size)

    @property
    def total_size(self):
        return self.payload_size + self.followup_size

    @staticmethod
    def load_from(fd: io.IOBase):
        data = fd.read(IntroSectionHeader.STRUCT.size)
        type, payload_size, followup_size = IntroSectionHeader.STRUCT.unpack(data)
        return IntroSectionHeader(type, payload_size, followup_size)

@attr.s
class IntroSection():
    header = attr.ib(type=IntroSectionHeader)
    payload = attr.ib(type=bytes, default=b'')