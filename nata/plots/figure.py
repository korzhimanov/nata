# -*- coding: utf-8 -*-
from copy import copy
from math import ceil

import attr
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from attr.validators import and_
from attr.validators import in_
from attr.validators import instance_of
from attr.validators import optional
from pkg_resources import resource_filename

from nata.plots import PlotTypes
from nata.plots.axes import Axes
from nata.plots.data import PlotData
from nata.utils.attrs import filter_kwargs


@attr.s
class Figure:

    # axes contained in the figure
    _axes: list = attr.ib(init=False, repr=False)

    # backend objects
    _plt: attr.ib(init=False, repr=False)
    _mpl: attr.ib(init=False, repr=False)

    # backend figure object
    _fig: attr.ib(init=False, repr=False)

    # backend object options
    figsize: tuple = attr.ib(
        default=(9, 6),
        validator=attr.validators.instance_of((tuple, np.ndarray)),
    )
    nrows: int = attr.ib(default=1)
    ncols: int = attr.ib(default=1)

    # style-related variables
    style: str = attr.ib(
        default="light",
        validator=optional(and_(instance_of(str), in_(("light", "dark")))),
    )
    fname: str = attr.ib(default=None, validator=optional(instance_of(str)))
    rc: dict = attr.ib(repr=False, default={})

    @property
    def axes(self) -> dict:
        return {axes.index: axes for axes in self._axes}

    # TODO: add metadata to attributes to identify auto state

    def __attrs_post_init__(self):

        # initialize list of axes objects
        self.init_axes()

        # set plotting style
        self.set_style()

        # initialize plotting backend
        self.init_backend()

        # open figure object
        self.open()

    def init_axes(self):
        self._axes = []

    def init_backend(self):
        self._plt = plt
        self._mpl = mpl

    def open(self):
        # TODO: generalize this for arbitrary backend
        self._fig = self._plt.figure(figsize=self.figsize)

    def close(self):
        self._plt.close(self._fig)

    def reset(self):
        self.close()
        self.open()

    def set_style(self):

        if not self.fname:
            self.fname = resource_filename(
                __name__, "styles/" + self.style + ".rc"
            )

    def show(self):
        # TODO: generalize this for arbitrary backend
        with mpl.rc_context(fname=self.fname, rc=self.rc):
            dummy = self._plt.figure()
            new_manager = dummy.canvas.manager
            new_manager.canvas.figure = self._fig

            self._fig.tight_layout()
            self._plt.show()

    def _repr_html_(self):
        self.show()

    def save(self, path, dpi=150):
        # TODO: generalize this for arbitrary backend
        with mpl.rc_context(fname=self.fname, rc=self.rc):
            self._fig.savefig(path, dpi=dpi, bbox_inches="tight")

    def copy(self):

        self.close()

        new = copy(self)
        new.open()

        for axes in new.axes.values():
            axes._fig = new

        return new

    def add_axes(self, **kwargs):

        new_index = len(self.axes) + 1

        if new_index > (self.nrows * self.ncols):
            # increase number of rows
            # TODO: really?
            self.nrows += 1

            for axes in self.axes.values():
                axes.redo_plots()

        axes_kwargs = filter_kwargs(Axes, **kwargs)
        axes = Axes(fig=self, index=new_index, **axes_kwargs)
        self._axes.append(axes)

        return axes

    def add_plot(self, axes: Axes, plot: PlotTypes, data: PlotData, **kwargs):
        p = axes.add_plot(plot=plot, data=data, **kwargs)

        axes.update_plot_options()
        axes.update()

        return p

    def __mul__(self, other):

        new = copy(self)

        for key, axes in new.axes.items():

            if key in other.axes:
                for plot in other.axes[key]._plots:
                    axes.add_plot(plot=plot)

            axes.redo_plots()

        new.close()

        return new

    def __add__(self, other):

        new = self.copy()

        new.nrows = ceil((len(new._axes) + len(other._axes)) / new.ncols)

        for axes in new._axes:
            axes.redo_plots()

        for axes in other._axes:
            # get a copy of old axes
            new_axes = axes.copy()

            # reset parent figure object
            new_axes._fig = new

            # redo plots in new axes
            new_axes.index = len(new._axes) + 1
            new_axes.redo_plots()

            # add axes to new list
            new._axes.append(new_axes)

        new.close()

        return new