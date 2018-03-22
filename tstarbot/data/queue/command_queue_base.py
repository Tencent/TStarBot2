class CommandBase(object):
    def __init__(self, uid):
        self._uid = uid

    def cmd_type(self):
        raise NotImplementedError

class CommandQueueBase(object):
    def put(self, idx, cmd):
        pass

    def get(self, idx, cmd):
        pass

    def clear_all(self):
        pass