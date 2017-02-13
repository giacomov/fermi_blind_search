class ltfException(RuntimeError):
  def __init__(self,message):
    self.message = message
    super( RuntimeError, self ).__init__(message)
  pass
pass
