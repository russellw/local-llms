class _Node:
    __slots__ = ("children", "weight", "is_word")

    def __init__(self):
        self.children = {}
        self.weight = 0
        self.is_word = False


class Autocomplete:
    def __init__(self):
        self.root = _Node()
        self._count = 0

    def add(self, word: str, weight: int = 1) -> None:
        if not word:
            return
        node = self.root
        for ch in word:
            node = node.children.setdefault(ch, _Node())
        if not node.is_word:
            node.is_word = True
            self._count += 1
        node.weight = weight

    def suggest(self, prefix: str, k: int = 5) -> list[str]:
        if k <= 0:
            return []
        node = self.root
        for ch in prefix:
            node = node.children.get(ch)
            if node is None:
                return []

        found = []
        stack = [(node, prefix)]
        while stack:
            n, word = stack.pop()
            if n.is_word:
                found.append((-n.weight, word))
            for ch, child in n.children.items():
                stack.append((child, word + ch))

        found.sort()
        return [w for _, w in found[:k]]

    def __len__(self) -> int:
        return self._count
