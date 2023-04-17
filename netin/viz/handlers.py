import logging
from typing import Set
from typing import List
from typing import Union

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib import rc
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns

from netin.utils import constants as const
from netin.viz.constants import *
from netin.generators.graph import Graph
from netin.stats.distributions import fit_power_law
from netin.stats.distributions import get_fraction_of_minority
from netin.stats.distributions import get_gini_coefficient
from netin.stats.distributions import get_disparity


def reset_style():
    sns.reset_orig()


def set_paper_style(font_scale=1.0):
    sns.set_context("paper", font_scale=font_scale)
    rc('font', family='serif')
    rc('lines', linewidth=1.0)
    rc('axes', linewidth=0.5)
    rc('xtick.major', width=0.5)
    rc('ytick.major', width=0.5)


def _get_edge_color(s: int, t: int, g: Graph):
    if g.get_class_value(s) == g.get_class_value(t):
        if g.get_class_value(s) == const.MINORITY_VALUE:
            return COLOR_MINORITY
        else:
            return COLOR_MAJORITY
    return COLOR_MIXED


def _get_class_label_color(class_label: str, ylabel: str = None) -> str:
    if ylabel in MINORITY_CURVE and class_label is None:
        return COLOR_MINORITY

    return COLOR_MINORITY if class_label == const.MINORITY_LABEL \
        else COLOR_MAJORITY if class_label == const.MAJORITY_LABEL \
        else COLOR_BLACK


def _save_plot(fig, fn=None, **kwargs):
    dpi = kwargs.pop('dpi', DPI)
    wspace = kwargs.pop('wspace', None)
    hspace = kwargs.pop('hspace', None)
    fig.tight_layout()
    fig.subplots_adjust(wspace=wspace, hspace=hspace)
    if fn is not None and fig is not None:
        fig.savefig(fn, dpi=dpi, bbox_inches='tight')
        logging.info("%s saved" % fn)
    plt.show()
    plt.close()


def _get_grid_info(total_subplots: int, nc: int = None) -> (int, int):
    nc = total_subplots if nc is None else nc  # min(MAX_PLOTS_PER_ROW, total_subplots) if nc is None else nc
    nr = int(np.ceil(total_subplots / nc))  # int(np.ceil(nc / MAX_PLOTS_PER_ROW))
    return nc, nr


def _add_class_legend(fig, **kwargs):
    maj_patch = mpatches.Patch(color=COLOR_MAJORITY, label='majority')
    min_patch = mpatches.Patch(color=COLOR_MINORITY, label='minority')
    bbox = kwargs.get('bbox', (1.04, 1))
    loc = kwargs.get('loc', "upper left")
    fig.legend(handles=[maj_patch, min_patch], bbox_to_anchor=bbox, loc=loc)


def plot_graphs(iter_graph: Set[Graph], share_pos=False, fn=None, **kwargs):
    nc = kwargs.pop('nc', None)
    nc, nr = _get_grid_info(len(iter_graph), nc=nc)
    cell_size = kwargs.get('cell_size', DEFAULT_CELL_SIZE)

    fig, axes = plt.subplots(nr, nc, figsize=(nc * cell_size, nr * cell_size), sharex=False, sharey=False)
    node_size = kwargs.get('node_size', 1)
    node_shape = kwargs.get('node_shape', 'o')
    edge_width = kwargs.get('edge_width', 0.02)
    edge_style = kwargs.get('edge_style', 'solid')
    edge_arrows = kwargs.get('edge_arrows', True)
    arrow_style = kwargs.get('arrow_style', '-|>')
    arrow_size = kwargs.get('arrow_size', 2)

    pos = None
    same_n = len(set([g.number_of_nodes() for g in iter_graph])) == 1
    for c, g in enumerate(iter_graph):
        ax = axes[c]
        pos = nx.spring_layout(g) if pos is None or not share_pos or not same_n else pos

        # nodes
        maj = g.graph['class_values'][g.graph['class_labels'].index("M")]
        nodes, node_colors = zip(
            *[(node, COLOR_MAJORITY if data[g.graph['class_attribute']] == maj else COLOR_MINORITY)
              for node, data in g.nodes(data=True)])
        nx.draw_networkx_nodes(g, pos, nodelist=nodes, node_size=node_size, node_color=node_colors,
                               node_shape=node_shape, ax=ax)

        # edges
        edges = g.edges()
        edges, edge_colors = zip(*[((s, t), _get_edge_color(s, t, g)) for s, t in edges])
        nx.draw_networkx_edges(g, pos, ax=ax, edgelist=edges, edge_color=edge_colors,
                               width=edge_width, style=edge_style, arrows=edge_arrows, arrowstyle=arrow_style,
                               arrowsize=arrow_size)

        # final touch
        ax.set_axis_off()
        ax.set_title(g.graph['model'])

    # legend
    _add_class_legend(fig, **kwargs)
    _save_plot(fig, fn, **kwargs)


def plot_distribution(data: Union[pd.DataFrame, List[pd.DataFrame]], col_name: Union[str, List],
                      get_x_y_from_df_fnc: callable, fn=None, **kwargs):
    iter_data = [data] if type(data) == pd.DataFrame else data
    nc = kwargs.pop('nc', None)
    nc, nr = _get_grid_info(len(iter_data), nc=nc)
    cell_size = kwargs.pop('cell_size', DEFAULT_CELL_SIZE)
    iter_column = [col_name] * (nc * nr) if type(col_name) == str else col_name

    scatter = kwargs.pop('scatter', False)
    hue = kwargs.pop('hue', None)
    sharex = kwargs.pop('sharex', False)
    sharey = kwargs.pop('sharey', False)
    xy_fnc_name = get_x_y_from_df_fnc.__name__
    ylabel = xy_fnc_name.replace("get_", '').upper()
    ylabel = kwargs.pop('ylabel', ylabel)
    xlabel = kwargs.pop('xlabel', None)
    xlim = kwargs.pop('xlim', None)
    ylim = kwargs.pop('ylim', None)
    common_norm = kwargs.pop('common_norm', False)
    log_scale = kwargs.pop('log_scale', (False, False))
    class_label_legend = kwargs.pop('class_label_legend', True)
    hline_fnc = kwargs.pop('hline_fnc', None)
    vline_fnc = kwargs.pop('vline_fnc', None)
    suptitle = kwargs.pop('suptitle', None)
    cuts = kwargs.pop('cuts', None)
    gini_fnc = kwargs.pop('gini_fnc', None)
    me_fnc = kwargs.pop('me_fnc', None)
    beta = kwargs.pop('beta', None)
    wspace = kwargs.pop('wspace', None)
    hspace = kwargs.pop('hspace', None)

    w, h = cell_size if type(cell_size) == tuple else (cell_size, cell_size)
    fig, axes = plt.subplots(nr, nc, figsize=(nc * w, nr * h), sharex=sharex, sharey=sharey)

    for cell, df in enumerate(iter_data):
        row = cell // nc
        col = cell % nc
        _col_name = iter_column[cell]

        ax = axes if nr == nc == 1 else axes[cell] if nr == 1 else axes[row, col]

        class_label: str
        iter_groups = df.groupby(hue) if hue is not None else [(None, df)]
        f_m = df.query("class_label == @const.MINORITY_LABEL").shape[0] / df.shape[0]
        for class_label, group in iter_groups:
            total = df[_col_name].sum() if common_norm else group[_col_name].sum()
            xs, ys = get_x_y_from_df_fnc(group, _col_name, total)
            plot = ax.scatter if scatter else ax.plot
            plot(xs, ys, label=class_label, color=_get_class_label_color(class_label, xy_fnc_name), **kwargs)

            if hline_fnc:
                hline_fnc(ax.axhline, group)
            if vline_fnc:
                vline_fnc(ax.axvline, group)
            if me_fnc:
                me_fnc(ax, f_m, ys, beta)
            if gini_fnc:
                gini_fnc(ax, ys, cuts)

        if log_scale[0]:
            ax.set_xscale('log')
        if log_scale[1]:
            ax.set_yscale('log')
        if xlim:
            ax.set_xlim(xlim)
        if ylim:
            ax.set_ylim(ylim)
        if ylabel and ((sharey and col == 0) or (not sharey)):
            ax.set_ylabel(ylabel)
        if xlabel is None:
            ax.set_xlabel(_col_name)
        elif (sharex and row == nr - 1) or (not sharex):
            ax.set_xlabel(xlabel)

        ax.set_title(df.name)

    # suptitle
    if suptitle is not None:
        fig.suptitle(suptitle)

    # legend
    if hue is not None and class_label_legend:
        _add_class_legend(fig, **kwargs)

    # save figure
    _save_plot(fig, fn, wspace=wspace, hspace=hspace, **kwargs)


def _show_cuts(axline, data):
    for c in const.INEQUALITY_CUTS:
        axline(c, ls='--', color='grey', alpha=0.5)


def _show_beta(axline, data):
    axline(const.INEQUITY_BETA, ls='--', color='grey', alpha=0.5)
    axline(-const.INEQUITY_BETA, ls='--', color='grey', alpha=0.5)


def plot_disparity(iter_data: Union[pd.DataFrame, List[pd.DataFrame]], x: Union[str, List], fn=None, **kwargs):
    gap = 0.04
    kwargs['class_label_legend'] = False
    kwargs['xlabel'] = INEQUITY_AXIS_LABEL
    kwargs['ylabel'] = INEQUALITY_AXIS_LABEL
    kwargs['ylim'] = (0.0 - gap, 1.0 + gap)
    kwargs['xlim'] = (-1.0 - gap, 1.0 + gap)
    kwargs['scatter'] = True
    kwargs['hline_fnc'] = _show_cuts
    kwargs['vline_fnc'] = _show_beta

    plot_distribution(iter_data,
                      col_name=x,
                      get_x_y_from_df_fnc=get_disparity,
                      fn=fn, **kwargs)


def plot_gini_coefficient(iter_data: Union[pd.DataFrame, List[pd.DataFrame]], x: Union[str, List], fn=None, **kwargs):
    def show_gini(ax, ys, cuts):
        gini, x, y, va, ha, color = get_gini_label(ys, cuts)
        ax.text(s=gini,
                x=x, y=y,
                color=color,
                transform=ax.transAxes,
                ha=ha, va=va)

    def get_gini_label(ys, cuts=None) -> (str, float, str):
        from netin.stats import ranking
        # value
        gini_global = ys[-1]
        # label
        ineq = ranking.get_ranking_inequality_class(gini_global, cuts)
        # position
        right = False
        bottom = np.any(np.array(ys[:5]) > 0.8)
        y = 0.01 if bottom else 0.97
        x = 0.02
        va = 'bottom' if bottom else 'top'
        ha = 'right' if right else 'left'
        c = 'grey'
        return f"Gini={gini_global:.3f}\n{ineq}", x, y, va, ha, c

    cuts = kwargs.pop('cuts', const.INEQUALITY_CUTS)

    kwargs['class_label_legend'] = False
    kwargs['hline_fnc'] = _show_cuts
    kwargs['gini_fnc'] = show_gini
    kwargs['xlabel'] = RANKING_LABEL
    kwargs['ylabel'] = GINI_TOPK_AXIS_LABEL
    kwargs['ylim'] = (-0.01, 1.01)

    plot_distribution(iter_data,
                      col_name=x,
                      get_x_y_from_df_fnc=get_gini_coefficient,
                      fn=fn, **kwargs)


def plot_fraction_of_minority(iter_data: Union[pd.DataFrame, List[pd.DataFrame]], x: Union[str, List],
                              fn=None, **kwargs):
    gap = 0.02

    def show_me(ax, f_m, ys, beta):
        me, x, y, va, ha, color = get_me_label(f_m, ys, beta)
        ax.text(s=me,
                x=x, y=y,
                color=color,
                transform=ax.transAxes,
                ha=ha, va=va)

    def get_me_label(f_m, ys, beta=None) -> (str, float, str):
        from netin.stats import ranking
        # value
        me = ranking.get_ranking_inequity(f_m, ys)
        # label
        ineq = ranking.get_ranking_inequity_class(me, beta)
        # position
        right = False
        bottom = np.any(np.array(ys[:5]) > 0.8)
        y = 0 + (gap * 2) if bottom else 1 - (gap * 2)
        x = 0 + (gap * 2)

        if f_m <= 0.2 and bottom:
            right = True
            bottom = False
            y = 0 + (gap * 2) if bottom else 1 - (gap * 2)
            x = 0 + (gap * 2)

            if np.any(np.array(ys[5:]) > 0.8):
                # above minority
                right = False
                bottom = True
                y = f_m + (gap * 2)
                x = 0 + (gap * 2)

        va = 'bottom' if bottom else 'top'
        ha = 'right' if right else 'left'
        c = 'grey'
        return f"ME={me:.3f}\n{ineq}", x, y, va, ha, c

    def show_minority(axline, data):
        axline(data.query("class_label==@const.MINORITY_LABEL").shape[0] / data.shape[0], color="black", linestyle='--')

    beta = kwargs.pop('beta', const.INEQUITY_BETA)
    kwargs['class_label_legend'] = False
    kwargs['hline_fnc'] = show_minority
    kwargs['me_fnc'] = show_me
    kwargs['xlabel'] = RANKING_LABEL
    kwargs['ylabel'] = FM_TOPK_AXIS_LABEL
    kwargs['ylim'] = (0. - gap, 1. + gap)

    plot_distribution(iter_data,
                      col_name=x,
                      get_x_y_from_df_fnc=get_fraction_of_minority,
                      fn=fn, **kwargs)


def plot_powerlaw_fit(data: Union[pd.DataFrame, List[pd.DataFrame]], col_name: Union[str, List], kind: str,
                      fn=None, **kwargs):

    if kind not in TYPE_OF_DISTRIBUTION:
        raise ValueError(f"kind must be one of {TYPE_OF_DISTRIBUTION}")

    iter_data = [data] if type(data) == pd.DataFrame else data
    nc = kwargs.pop('nc', None)
    nc, nr = _get_grid_info(len(iter_data), nc=nc)
    cell_size = kwargs.pop('cell_size', DEFAULT_CELL_SIZE)
    iter_column = [col_name] * (nc * nr) if type(col_name) == str else col_name

    # whole plot
    sharex = kwargs.pop('sharex', False)
    sharey = kwargs.pop('sharey', False)
    log_scale = kwargs.pop('log_scale', (False, False))
    xlabel = kwargs.pop('xlabel', None)
    ylabel = kwargs.pop('ylabel', "p(X≥x)" if kind == "ccdf" else "p(X<x)" if kind == 'cdf' else "p(X=x)" if kind == 'pdf' else None)
    verbose = kwargs.pop('verbose', False)
    wspace = kwargs.pop('wspace', None)
    hspace = kwargs.pop('hspace', None)

    # outer legend
    hue = kwargs.pop('hue', None)
    bbox = kwargs.pop('bbox', (1.0, 0.9))

    # inner legend
    fontsize = kwargs.pop('fontsize', None)
    loc = kwargs.pop('loc', None)

    # plot
    w, h = cell_size if type(cell_size) == tuple else (cell_size, cell_size)
    fig, axes = plt.subplots(nr, nc, figsize=(nc * w, nr * h), sharex=sharex, sharey=sharey)

    for cell, df in enumerate(iter_data):
        row = cell // nc
        col = cell % nc
        _col_name = iter_column[cell]

        ax = axes if nr == nc == 1 else axes[cell] if nr == 1 else axes[row, col]

        class_label: str
        iter_groups = df.groupby(hue) if hue is not None else [(None, df)]
        for class_label, group in iter_groups:
            group_nonzero = group.query(f"{_col_name}>0")
            discrete = group_nonzero[_col_name].dtype == np.int64
            fit = fit_power_law(group_nonzero.loc[:, _col_name].values, discrete=discrete, verbose=verbose)

            color = _get_class_label_color(class_label)

            efnc = fit.plot_ccdf if kind == "ccdf" else fit.plot_cdf if kind == 'cdf' else fit.plot_pdf
            fnc = fit.power_law.plot_ccdf if kind == "ccdf" else fit.power_law.plot_cdf if kind == 'cdf' \
                else fit.power_law.plot_pdf

            ax = efnc(label=r"Empirical", ax=ax, color=color, **kwargs)
            ax = fnc(label=f'Powerlaw $\gamma={fit.alpha:.2f}$', linestyle='--', ax=ax, color=color, **kwargs)

            # legend inside: empirical vs powerlaw
            handles, labels = ax.get_legend_handles_labels()
            loc = loc if loc is not None else 4 if kind == 'cdf' else 1
            leg = ax.legend(handles, labels, loc=loc, fontsize=fontsize)
            leg.draw_frame(False)

        if log_scale[0]:
            ax.set_xscale('log')
        if log_scale[1]:
            ax.set_yscale('log')
        if ylabel is not None and ((sharey and col == 0) or (not sharey)):
            ax.set_ylabel(ylabel)
        if xlabel is None:
            ax.set_xlabel(_col_name)
        elif (sharex and row == nr - 1) or (not sharex):
            ax.set_xlabel(xlabel)

        ax.set_title(df.name)

    # legend
    if hue:
        kwargs['bbox'] = bbox
        _add_class_legend(fig, **kwargs)
    _save_plot(fig, fn, wspace=wspace, hspace=hspace, **kwargs)
