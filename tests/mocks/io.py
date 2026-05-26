from io import StringIO


class MockStringIO(StringIO):
    def __init__(self, **kwargs):
        super(MockStringIO, self).__init__(**kwargs)
        self.final_content = None

    def close(self):
        self.final_content = self.getvalue()
        super(MockStringIO, self).close()
