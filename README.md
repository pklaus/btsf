## btfs - Binary Time Series File

This is a module to store time series data. It uses its own binary file format .btfs with the following **objectives**:

* small output file size
* appendable
* fast to read and write
* flexible usage for different scenarios
* ability to store metadata
* ability to store annotations
* targeted at Python (though supporting other languages should be rather straight-forward)
* possibility to specify details such as byte order, padding

Quick description of the file structure:

The output .btfs file consists of:

```
File Signature (fixed)
(32 bytes)

header (JSON encoded)
(variable length)

annotations (JSON encoded)
(variable length)

RAW Data chunks
(variable length)
```

A typical use case for btfs is:
* Data acquisition of a couple of variables, all sampled at the same time.
* The same file can be opened again for appending to its end in case the acquisition has to be restarted.
* A GUI to visualize the file's content can be used to annotate the time series and the annotations can be stored in the file.

What btfs is not suited for, at least not perfectly:
* event-based data with varying value types

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
    f.log_new_samples(1.1, 2.2, 0xf0f0f0f0f0f0f0f0, 1)
    f.log_new_samples(3.3, 4.4, 0xffffffffffffffff, 2)
    f.log_new_samples(5.0, 1.0, 0x123456789ABCDEF1, 3)
    f.close()
```
