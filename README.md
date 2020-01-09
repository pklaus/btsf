## btfs - Binary Time Series File

This is a module to store time series data in a custom binary file format (.btfs) with the following **objectives**:

* small file size
* appendable
* fast to read and write
* easy to adapt to new scenarios
* ability to store metadata (units, annotations, ...)
* targeted at Python (adding support for other languages should be rather straight-forward)
* possibility to tune implementation details such as byte order or padding

Quick description of the file structure of a .btfs file:

```
File Signature (fixed)
(32 bytes)

one ore more header sections (JSON encoded)
(8-byte size field + variable length padded 8-byte boundary with 0x00)

concatenated packed structured data
(x entries of fixed structure and length)
```

A typical use case for btfs is:

* Data acquisition of a couple of variables, all sampled at the same time.
* The same file can be opened again for appending to its end in case the acquisition has to be restarted.
* A GUI to visualize the file's content can be used to annotate the time series and the annotations can be stored in the file.

What btfs is not suited for, at least not perfectly:

* event-based data with varying number of values or varying value types

### Installation

    pip install --upgrade https://github.com/pklaus/btsf/archive/master.zip

### Example Usage

```python

from btsf import Metric, BinaryTimeSeriesFile, Type

metrics = [
    Metric('time', Type.Double),
    Metric('power', Type.Float),
    Metric('counter', Type.UInt64),
    Metric('flags', Type.UInt8),
]

with BinaryTimeSeriesFile.create('test.btsf', metrics) as f:
    f.append(1.1, 2.2, 0xf0f0f0f0f0f0f0f0, 1)
    f.append(3.3, 4.4, 0xffffffffffffffff, 2)
    f.append(5.0, 1.0, 0x123456789ABCDEF1, 3)
```

Checking what's in a .btsf file is easy with the supplied CLI:

```bash
btsf info test.btsf
```

resulting in the following output:

```
test.btsf - Number of entries: 3
Metrics:
time (Type.Double)   power (Type.Float)   counter (Type.UInt64)   flags (Type.UInt8)
entries:
(1.1, 2.200000047683716, 17361641481138401520, 1)
(3.3, 4.400000095367432, 18446744073709551615, 2)
(5.0, 1.0, 1311768467463790321, 3)
```
