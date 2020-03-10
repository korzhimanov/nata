# -*- coding: utf-8 -*-
from typing import List
from typing import Optional

import numpy as np

from IPython.display import display
from ipywidgets import Layout
from ipywidgets import widgets
from nata.containers import DatasetCollection
from nata.containers import GridDataset
from nata.containers import ParticleDataset
from nata.plots import DefaultGridPlotTypes
from nata.plots import DefaultParticlePlotType
from nata.plots import PlotTypes
from nata.plots.axes import Axes
from nata.plots.data import PlotData
from nata.plots.data import PlotDataAxis
from nata.plots.figure import Figure
from nata.plugins.register import register_container_plugin
from nata.utils.attrs import filter_kwargs
from nata.utils.env import inside_notebook
from nata.utils.exceptions import NataInvalidPlot


@register_container_plugin(GridDataset, name="plot")
def plot_grid_dataset(
    dataset: GridDataset,
    fig: Optional[Figure] = None,
    axes: Optional[Axes] = None,
    interactive: bool = True,
    **kwargs,
):

    if len(dataset) > 1 and inside_notebook() and interactive:
        build_interactive_tools(dataset, **kwargs)

    else:
        plot_data = dataset.plot_data()
        plot_type = dataset.plot_type

        # build figure
        fig = build_figure(
            plot_data=plot_data,
            plot_type=plot_type,
            fig=fig,
            axes=axes,
            **kwargs,
        )
        return fig


@register_container_plugin(ParticleDataset, name="plot")
def plot_particle_dataset(
    dataset: ParticleDataset,
    quants: List[str] = [],
    c_quant: Optional[str] = None,
    fig: Optional[Figure] = None,
    axes: Optional[Axes] = None,
    **kwargs,
) -> Figure:

    # raise error if dataset has more than one data object
    if len(dataset) != 1:
        raise NataInvalidPlot

    # get default plot type for grids
    # TODO: make this an argument?
    plot_type = DefaultParticlePlotType

    # build plot axes object
    # TODO: make this a method of the dataset?

    if c_quant:
        quants.append(c_quant)

    plot_data = dataset.plot_data(quants=quants)
    plot_type = dataset.plot_type

    # build figure
    fig = build_figure(
        plot_data=plot_data, plot_type=plot_type, fig=fig, axes=axes, **kwargs
    )

    return fig


@register_container_plugin(DatasetCollection, name="plot")
def plot_collection(
    collection: DatasetCollection,
    order: Optional[list] = [],
    styles: Optional[dict] = {},
    # fig: Optional[Figure] = None,
    # axes: Optional[Axes] = None,
    **kwargs,
) -> Figure:

    # check if collection is not empty
    if not collection.store:
        raise ValueError("Collection is empty.")

    # check if order elements exist in collection
    for key in order:
        if key not in collection.store.keys():
            raise ValueError(
                f"Order key `{key}` is not a part of the collection."
            )

    if len(order) > 0 and len(order) < len(collection.store):

        # get collection keys as list
        unused_keys = list(collection.store.keys())

        # remove elemets already in order
        for key in order:
            unused_keys.remove(key)

        # add unused keys to order
        for key in unused_keys:
            order.append(key)

    elif not order:
        order = collection.store.keys()

    # build figure object
    fig_kwargs = filter_kwargs(Figure, **kwargs)

    fig = Figure(**fig_kwargs)

    for key in order:
        # get dataset
        dataset = collection.store[key]

        # get dataset plot specific kwargs
        ds_kwargs = {}
        if key in styles:
            ds_kwargs = styles[key]

        # add new axes
        axes_kwargs = filter_kwargs(Axes, **ds_kwargs)
        axes = fig.add_axes(**axes_kwargs)

        plot_type = DefaultGridPlotTypes[dataset.grid_dim]

        # TODO: make this a method of the dataset?
        # build plot axes object
        plot_axes = []

        for ds_axes in dataset.axes:
            new_axes = PlotDataAxis(
                name=ds_axes.name,
                label=ds_axes.label,
                units=ds_axes.unit,
                type=ds_axes.axis_type,
                data=np.array(ds_axes),
            )

            plot_axes.append(new_axes)

        # build data object
        data = PlotData(
            name=dataset.name,
            label=dataset.label,
            units=dataset.unit,
            data=np.array(dataset),
            time=np.array(dataset.time),
            time_units=dataset.time.unit,
            axes=plot_axes,
        )

        # build plot
        plot_kwargs = filter_kwargs(plot_type, **ds_kwargs)
        axes.add_plot(plot_type=plot_type, data=data, **plot_kwargs)

        axes.update()

    fig.close()

    return fig


def build_figure(
    plot_data: PlotData,
    plot_type: PlotTypes,
    fig: Optional[Figure] = None,
    axes: Optional[Axes] = None,
    **kwargs,
) -> Figure:
    # build figure
    if fig is None:

        fig_kwargs = filter_kwargs(Figure, **kwargs)
        fig = Figure(**fig_kwargs)

        # ignore axes
        axes = None

    # build axes
    if axes is None:

        axes_kwargs = filter_kwargs(Axes, **kwargs)
        axes = fig.add_axes(**axes_kwargs)

    # 4. build plot
    plot_kwargs = filter_kwargs(plot_type, **kwargs)
    axes.add_plot(plot_type=plot_type, data=plot_data, **plot_kwargs)

    axes.update()

    fig.close()

    return fig


def build_interactive_tools(dataset, **kwargs):
    time = np.array(dataset.time)
    iteration = np.array(dataset.iteration)

    dropdown = widgets.Dropdown(
        options=["File Index", "Iteration", "Time"],
        value="File Index",
        disabled=False,
        layout=Layout(max_width="100px"),
        continuous_update=False,
    )

    slider = widgets.SelectionSlider(
        options=[f"{i}" for i in np.arange(len(dataset.iteration))],
        value=f"{0}",
        disabled=False,
        continuous_update=False,
        orientation="horizontal",
        readout=True,
    )

    def dropdown_change(change):

        if change.old in ["Time", "Iteration"]:
            options = np.array(slider.options).astype(np.float)
            n = np.argmax(options >= float(slider.value)).item()
        else:
            n = int(slider.value)

        with out.hold_trait_notifications():
            if change.new == "Time":
                slider.options = [f"{i:.2f}" for i in time]
                slider.value = f"{time[n]:.2f}"

            elif change.new == "Iteration":
                slider.options = [f"{i:d}" for i in iteration]
                slider.value = f"{iteration[n]:d}"
            else:
                slider.options = [f"{i:n}" for i in np.arange(len(iteration))]
                slider.value = f"{n:d}"

    dropdown.observe(dropdown_change, names=["value"], type="change")

    ui = widgets.HBox([dropdown, slider])

    def update_figure(sel):
        if dropdown.value == "Time":
            n = np.argmax(time >= float(sel)).item()
        elif dropdown.value == "Iteration":
            n = np.argmax(iteration >= int(sel)).item()
        else:
            n = int(sel)

        plot_data = dataset[n].plot_data()
        plot_type = dataset[n].plot_type

        # build figure
        fig = build_figure(plot_data=plot_data, plot_type=plot_type, **kwargs)

        return fig.show()

    out = widgets.interactive_output(update_figure, {"sel": slider})

    display(ui, out)
