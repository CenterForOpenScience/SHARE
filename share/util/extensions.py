from stevedore import extension


class ExtensionsError(Exception):
    pass


def on_error(manager, entrypoint, exception):
    raise exception


class Extensions:
    """Lazy singleton container for stevedore extensions.

    Loads each namespace when requested for the first time.
    """

    _managers = {}

    def __init__(self):
        raise NotImplementedError()

    @classmethod
    def get_names(cls, namespace):
        manager = cls._get_manager(namespace)
        return manager.names()

    @classmethod
    def get(cls, namespace, name):
        try:
            return cls._get_manager(namespace)[name].plugin
        except Exception as exc:
            raise ExtensionsError(f'Error loading extension ("{namespace}", "{name}")') from exc

    @classmethod
    def _get_manager(cls, namespace):
        manager = cls._managers.get(namespace)
        if manager is None:
            manager = cls._load_namespace(namespace)
        return manager

    @classmethod
    def _load_namespace(cls, namespace):
        try:
            manager = extension.ExtensionManager(namespace, on_load_failure_callback=on_error)
            cls._managers[namespace] = manager
            return manager
        except Exception as exc:
            raise ExtensionsError(f'Error loading extension namespace "{namespace}"') from exc
