class CommandBase(object):
  def __init__(self):
    self.cmd_id = 0  # command id
    self.cmd_type = 0
    self.idx = 0
    self.param = {}

  def __str__(self):
    return "id {}, type {}, idx {}, param {}".format(
      self.cmd_id, self.cmd_type, self.idx, self.param)


class CommandQueueBase(object):
  def __init__(self, cmd_id_base):
    self._cmd_dict = {}
    self._cmd_id = cmd_id_base

  def put(self, idx, cmd_type, param):
    cmd = CommandBase()
    cmd.cmd_id = self._cmd_id
    cmd.idx = idx
    cmd.cmd_type = cmd_type
    cmd.param = param

    if idx in self._cmd_dict:
      self._cmd_dict[idx].append(cmd)
    else:
      self._cmd_dict[idx] = [cmd]

    self._cmd_id += 1

  def get(self, idx):
    cmds = []

    if idx in self._cmd_dict:
      cmds = self._cmd_dict[idx]
      del self._cmd_dict[idx]

    return cmds

  def clear_all(self):
    self._cmd_dict.clear()
