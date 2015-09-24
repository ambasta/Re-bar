import importlib

from bson import ObjectId

from .base import BaseField

from mongo.utils import serialize


class ForeignKey(BaseField):

    def __init__(self, fkey_to, *args, **kwargs):
        self.lazy_load = False

        if isinstance(fkey_to, str):
            self.fkey_to = fkey_to
            self.lazy_load = True
        else:
            fkey_to = fkey_to
        super(ForeignKey, self).__init__(type=fkey_to, *args, **kwargs)

    def __getattr__(self, attribute):
        return getattr(self.value, attribute)

    def _lazy_load(self):
        self.lazy_load = False
        fullpath = self.fkey_to.split('.')
        module_path = '.'.join(fullpath[:-1])
        attr_path = fullpath[-1]
        module = importlib.import_module(module_path)
        f_type = getattr(module, attr_path)
        del(self.fkey_to)
        super(ForeignKey, self).__init__(type=f_type, required=self.required)

    def valueOf(self, value=None):
        if self.lazy_load:
            self._lazy_load()

        if not isinstance(value, self.f_type):
            if value is None:
                self.value = value
            elif isinstance(value, dict):
                self.value = self.f_type(**value)
            elif isinstance(value, ObjectId):
                self.value = self.f_type.find_one(value)
            else:
                raise TypeError(
                    'ForeignKey expects values of type {}. Got {}'.format(
                        self.f_type, value
                    )
                )
        else:
            self.value = value
        self.validate()
        return self

    def serialize(self, recurse=True):
        if recurse:
            return serialize(self.value)

        if self.value is None:
            return None

        return self.value._id
