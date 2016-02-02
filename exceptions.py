

class Exceptions(object):
    pass


class SomeException(Exceptions):
    def __init__(self):
        Exceptions.__init__(self)
