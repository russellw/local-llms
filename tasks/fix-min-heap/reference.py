class MinHeap:
    def __init__(self):
        self.items = []

    def push(self, value):
        self.items.append(value)
        i = len(self.items) - 1
        while i > 0:
            parent = (i - 1) // 2
            if self.items[i] >= self.items[parent]:
                break
            self.items[i], self.items[parent] = self.items[parent], self.items[i]
            i = parent

    def pop(self):
        if not self.items:
            raise IndexError("pop from an empty heap")
        top = self.items[0]
        last = self.items.pop()
        if self.items:
            self.items[0] = last
            i = 0
            n = len(self.items)
            while True:
                left, right = 2 * i + 1, 2 * i + 2
                smallest = i
                if left < n and self.items[left] < self.items[smallest]:
                    smallest = left
                if right < n and self.items[right] < self.items[smallest]:
                    smallest = right
                if smallest == i:
                    break
                self.items[i], self.items[smallest] = (
                    self.items[smallest],
                    self.items[i],
                )
                i = smallest
        return top

    def peek(self):
        if not self.items:
            raise IndexError("peek at an empty heap")
        return self.items[0]

    def __len__(self):
        return len(self.items)
