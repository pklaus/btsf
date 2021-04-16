import enum

import attr

__all__ = ["Metric", "MetricType"]


class MetricType(enum.Enum):
    # pylint:disable=bad-whitespace
    # fmt: off
    Float =  "f"
    Double = "d"
    Int8 =   "b"
    UInt8 =  "B"
    Int16 =  "h"
    UInt16 = "H"
    Int32 =  "l"
    UInt32 = "L"
    Int64 =  "q"
    UInt64 = "Q"
    # fmt: on


@attr.s
class Metric:
    identifier = attr.ib()
    type = attr.ib(type=MetricType)
    name = attr.ib(default="", type=str)
    unit = attr.ib(default="", type=str)
    description = attr.ib(default="", type=str)
    is_time = attr.ib(default=False, type=bool)

    def to_dict(self):
        d = attr.asdict(self)
        d["type"] = self.type.value
        return d
        # return {
        #    'identifier': self.identifier,
        #    'type': self.type.value,
        #    'name': self.name,
        #    'unit': self.unit,
        #    'description': self.description,
        #    'is_time': self.is_time,
        # }
