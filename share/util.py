

class CyclicalDependency(Exception):
    pass


# Sort a list of nodes topographically, so a node is always preceded by its dependencies
class TopographicalSorter:

    # `nodes`: Iterable of objects
    # `dependencies`: Callable that takes a single argument (a node) and returns an iterable of its dependent nodes (or keys, if `key` is given)
    # `key`: Callable that takes a single argument (a node) and returns a unique key. If omitted, nodes will be compared for equality directly.
    def __init__(self, nodes, dependencies, key=None):
        self.__sorted = []
        self.__nodes = list(nodes)
        self.__visited = set()
        self.__visiting = set()
        self.__dependencies = dependencies
        self.__key = key
        self.__node_map = {key(n): n for n in nodes} if key else None

    def sorted(self):
        if not self.__nodes:
            return self.__sorted

        while self.__nodes:
            n = self.__nodes.pop(0)
            self.__visit(n)

        return self.__sorted

    def __visit(self, node):
        key = self.__key(node) if self.__key else node
        if key in self.__visiting:
            raise CyclicalDependency(key, self.__visiting)

        if key in self.__visited:
            return

        self.__visiting.add(key)
        for k in self.__dependencies(node):
            if k is not None:
                self.__visit(self.__get_node(k))

        self.__visited.add(key)
        self.__sorted.append(node)
        self.__visiting.remove(key)

    def __get_node(self, key):
        return self.__node_map[key] if self.__node_map else key
