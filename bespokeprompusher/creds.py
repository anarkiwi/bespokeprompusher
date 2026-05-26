import configparser


class Creds:
    def __init__(self, path):
        self._cfg = configparser.ConfigParser(interpolation=None)
        if not self._cfg.read(path):
            raise SystemExit(f"creds: cannot read {path}")

    def get(self, section, key):
        return self._cfg.get(section, key)
