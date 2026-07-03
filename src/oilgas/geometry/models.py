from dataclasses import dataclass


@dataclass(slots=True)
class Word:
    text: str

    x0: float
    y0: float

    x1: float
    y1: float

    block: int
    line: int
    word: int

    @property
    def center_x(self):
        return (self.x0 + self.x1) / 2

    @property
    def center_y(self):
        return (self.y0 + self.y1) / 2
