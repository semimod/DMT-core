from DMT.core import Plot
from pathlib import Path
import numpy as np
from typing import List


class Label:
    def __init__(
        self,
        x: float,
        y: float,
        text: str,
        width: str,
        anchor: str = "north",
        background: str = "white",
    ):
        self.x = x
        self.y = y
        self.text = text
        self.anchor = anchor
        self.width = width
        self.background = background

    def as_text(self, node_name):
        return (
            r"\node[anchor="
            + self.anchor
            + ",text width={},inner sep=.05cm,align=center,fill=".format(self.width)
            + self.background
            + "]"
            + "("
            + node_name
            + ") at (axis cs:{}, {}) {{".format(self.x, self.y)
            + self.text
            + "};\n"
        )


class Line:
    def __init__(
        self, x1: float, y1: float, x2: float, y2: float, label: Label = None, sty: str = "-stealth"
    ):
        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2
        self.label = label
        self.sty = sty

    def as_text(self, label_node_name):
        text = (
            r"\draw["
            + self.sty
            + "] (axis cs: {}, {}) -- (axis cs:{}, {});\n".format(
                self.x1, self.y1, self.x2, self.y2
            )
        )
        if self.label is not None:
            text += self.label.as_text(label_node_name)
        return text

    def scale(self, factor):
        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        l = np.sqrt(dx * dx + dy * dy)
        r = dy / dx
        new_l = factor * l
        dx_new = np.sign(dx) * new_l / np.sqrt(1 + r * r)
        dy_new = dx_new * r
        self.x2 = self.x1 + dx_new
        self.y2 = self.y1 + dy_new


# This can probably done nicer by overwriting new so that this inherits from Plot by I currently don't have time to investigate that


class TikzPostprocess:
    plot: Plot
    lines: List[Line]

    def __init__(self, plot: Plot):
        self.plot = plot
        self.lines = []

    def save_tikz(self, directory: str, *args, **kwargs):
        if not isinstance(directory, Path):
            directory = Path(directory)

        file = self.plot.save_tikz(directory, *args, **kwargs)

        file = directory / file
        contents = file.read_text()
        contents = contents.split(r"\end{axis}")
        assert len(contents) == 2

        head = contents[0]
        tail = contents[1]

        for i, arrow in enumerate(self.lines):
            head += arrow.as_text("arrow_label_{}".format(i))

        contents = head + "\end{axis}" + tail
        file.write_text(contents)

    def add_line(self, arrow: Line):
        self.lines.append(arrow)

    def remove_legend(self):
        self.plot.remove_legend()
