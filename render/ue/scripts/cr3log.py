# shared logger: unreal log + a text file in _log/ that Claude can read
import unreal, os
_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_log")
os.makedirs(_DIR, exist_ok=True)
class Log:
    def __init__(self, name):
        self.path = os.path.join(_DIR, name + ".txt"); open(self.path, "w").close()
    def __call__(self, *a):
        msg = "[CR3] " + " ".join(str(x) for x in a); unreal.log(msg)
        with open(self.path, "a") as f: f.write(msg + "\n")
