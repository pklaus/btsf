class BtsfError(Exception):
    pass


class BtsfNameError(NameError, BtsfError):
    pass


class UnknownFile(BtsfNameError):
    pass


class NoFurtherData(StopIteration, BtsfError):
    pass


class EmptyBtsfError(BtsfError):
    pass


class InvalidFileContent(BtsfNameError):
    pass


class InvalidIntroSection(BtsfNameError):
    pass
