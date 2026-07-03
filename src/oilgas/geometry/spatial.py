class SpatialIndex:
    def __init__(self, words):

        self.words = sorted(
            words,
            key=lambda w: (w.y0, w.x0),
        )
