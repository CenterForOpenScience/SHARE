from stevedore import extension


class Extensions:
    """Lazy singleton container for stevedore extensions.

    Loads each namespace when requested for the first time.
    """

    _managers = {}

    def __init__(self):
        raise NotImplementedError()

    @classmethod
    def get(cls, namespace, name):
        manager = cls._managers.get(namespace)
        if manager is None:
            manager = cls._load_namespace(namespace)
        return manager[name].plugin

    @classmethod
    def _load_namespace(cls, namespace):
        manager = extension.ExtensionManager(namespace)
        cls._managers[namespace] = manager
        return manager
