
class BtsfError(Exception):
    pass

class BtsfNameError(NameError, BtsfError):
    pass

class UnknownFileError(BtsfNameError):
    pass

class NoFurtherData(StopIteration, BtsfError):
    pass

class EmptyBtsfError(BtsfError):
    pass

class InvalidFileContentError(BtsfNameError):
    pass
