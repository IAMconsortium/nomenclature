from collections.abc import Mapping
from nomenclature.utils import parse_yaml


class CodeList(Mapping):
    """A thin wrapper around a dictionary for nomenclature codelists & attributes"""

    def __init__(self, name, data=None):
        self._codes = data or dict()
        self._name = name

    @property
    def name(self):
        return self._name

    def __setitem__(self, key, value):
        if key in self._codes:
            raise ValueError(f'Duplicate {self._name} key: {key}')
        self._codes[key] = value

    def __getitem__(self, k):
        return self._codes[k]

    def __iter__(self):
        return iter(self._codes)

    def __len__(self):
        return len(self._codes)

    def __repr__(self):
        return self._codes.__repr__()

    def parse_files(self, path, file=None, top_level_attr=None):
        """Parse all files in `path` and add them to the codelist

        Parameters
        ----------
        path
        file
        top_level_attr

        Returns
        -------
        Nomenclature
        """
        parse_yaml(path=path, codes=self, file=file, top_level_attr=top_level_attr)
        return self  # allows to do `foo = CodeList("foo").parse_files(path)`
