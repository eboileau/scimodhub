from io import StringIO


class MockStringIO(StringIO):
    def __init__(self, **kargs):
        super(MockStringIO, self).__init__(**kargs)
        self.final_content = None

    def close(self):
        self.final_content = self.getvalue()
        super(MockStringIO, self).close()
