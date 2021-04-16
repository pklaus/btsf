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

at least one intro section
(16-byte header + variable length payload + variable length reserved zero-bytes)

end of intro section header
(16 bytes)

concatenated packed structured data
(structure of fixed length * N, thus appendable!)
```

A typical use case for btfs is:

* Time series measurements of one or multiple variables (sampled at the same time).
* Appending (=adding) new measurements to file is always possible, eg. after a restart of the acquisition.
* The metadata of the file (stored in the intro sections of the file) can later be updated
  with additional information, such as data annotations, tags or similar.

What btfs is not suited for, at least not perfectly:

* event-based data with varying number of values or varying value types.

*Note: As the size of the introduction sections cannot be expanded, editing the metadata is only possible
within the limits of reserved extra space for the intro section, specified when creating the file.*

### Installation

    pip install --upgrade https://github.com/pklaus/btsf/archive/master.zip

### Example Usage

```python
from btsf import Metric, MetricType, BinaryTimeSeriesFile

metrics = [
    Metric('time', MetricType.Double),
    Metric('power', MetricType.Float),
    Metric('counter', MetricType.UInt64),
    Metric('flags', MetricType.UInt8),
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
time (MetricType.Double)   power (MetricType.Float)   counter (MetricType.UInt64)   flags (MetricType.UInt8)
entries:
(1.1, 2.200000047683716, 17361641481138401520, 1)
(3.3, 4.400000095367432, 18446744073709551615, 2)
(5.0, 1.0, 1311768467463790321, 3)
```
