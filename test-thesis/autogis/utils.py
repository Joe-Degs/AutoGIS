import os
from typing import Sequence
import geopandas
import pandas

import contextily as ctx
from pyproj import CRS
from shapely.geometry import Point

def load_csv(sep: str, *files: str, **kwargs) -> list[pandas.DataFrame]:
    """load csv file from filesystem"""
    assert len(files) == 2, "load_csv: expecting two files"
    assert all([os.path.isfile(f) for f in files]), \
        "load_csv: arguments must be valid csv files"
    return [pandas.read_csv(file, sep=sep or ',', **kwargs) \
        for file in files]

def reverse_geocode(coords: list[Point]) -> geopandas.GeoDataFrame:
    """reverse geocode list of shapely points

    """
    return geopandas.tools.reverse_geocode(coords)

def reverse_geocode_all(*data: list[Point]) \
    -> tuple[geopandas.GeoDataFrame]:
    """reverse geocode list of coordinates
    """
    return tuple(map(reverse_geocode, data))

def coords_from_df(df: pandas.DataFrame) -> list[Point]:
    """extract coordinates from csv file
    """
    return list(map(lambda x: Point(x[1].x, x[1].y), df.iterrows()))

def coords_from_geodata(geodata: geopandas.GeoDataFrame) \
        -> list[tuple[float]]:
    """return lat,long pairs from geodata with point geometry

    sample return value is [(1, 2), (3, 4)]
    """
    assert all('point' in t.lower() for t in geodata.geometry.geom_type.unique()), \
            "geometry must be points before extracting lat,long pairs"
    return [(p.x, p.y) for p in geodata.geometry]

def coords_from_multiple(*geodata: geopandas.GeoDataFrame) \
        -> tuple[list[tuple[float]]]:
    """
    """
    return tuple(map(coords_from_geodata, geodata))

def lat_long_from_coords(coords: list[tuple]) :
    """given a list of coordinates [ len(tuple)==2 ] extract first
    values as lattitude and second values a longitudes values
    """
    # get list of (lat, long) pairs from geodata
    coords = coords_from_geodata(origin)
    x, y = list(zip(*coords))[0], list(zip(*coords))[1]
    return list(x), list(y)


def nearest_node_ids(G: nx.MultiDiGraph, longitude: list[float],
        lattitude: list[float]) -> list[str]:
    """get the id's of nearest nodes around some coordinates in a
    graph
    """
    return ox.nearest_nodes(G, longitude, lattitude)

def nearest_node(nodes: geopandas.GeoDataFrame, node_ids: list[str]):
    """return a geopandas or geoseries selected from nodes based on
    node ids
    """
    return nodes.loc[nearest_node_id()]

def to_crs(crs: CRS | str, data: geopandas.GeoDataFrame) \
    -> geopandas.GeoDataFrame:
    """convert data to new CRS

    Returns:
        geopandas.GeoDataFrame: changed data
    """
    return data.to_crs(crs) if data.crs != crs \
        else data

class PlotArgs(dict):    
    """collects all the args required to do a static/interactive plot

    this is passed to all the plotting functions that rely these
    parameters for plotting

    Parameters
    -----------
    nrows=1 : int
        number of rows plot
    ncols=1 : int
        number of columns for plot
    figsize=(10, 10) : tuple[int, int]
        figure size of each graph space
    axis=True : bool
        show the axis of the resulting plot
    tight_layout=False : bool
        make plot a tight layout
    edges=True : bool
        plot edges/line of the network graph
    nodes=True : bool
        plot nodes/intersection of network graph

    line_color='gray' : str
        color of edges in plot
    node_color='gray' str
        color of nodes / intersection points in plot
    linewidth=0.7 : float | None
        line width of edges in plot
    line_alpha=0.5 : float | None
        opacity of edges in plot
    node_alpha=None : float | None
        opacity of the nodes in graph plot

    filepath=None : str | None
        path to file to save resulting plot
    tiles=False : bool
        add a basemap tile from an online tile service using contextily
        for static plots and folium for interactive plots
    title=None : str | None
        title of the plot
    static_tile=ctx.providers.CartoDB.Positron : xyzservices.lib.TileProvider
        online tile service to use for static plots
        see `ctx.providers` for more providers from contextily
    interactive_tile='OpenStreetMap' : str
        service to use for interactive plots
    callback=None : Func | None
        callback of signature `Func[fig, ax] -> None`, used to customize
        plot to the callers satisfaction
    """

    def __init__(self, add_keys=True, **kwargs):
        
        # add default keyword arguments to dict
        self.update(
                nrows=1,
                ncols=1,
                figsize=(10, 10),
                axis=True,
                tight_layout=True,
                edges=True,
                nodes=True,

                # generic kwargs for nodes/edges
                color='gray',
                alpha=0.5,

                # style for lines
                linewidth=0.7,
                linestyle='-',

                # styles for nodes/polygons
                markersize=20,
                marker='o',

                # static plot config
                basemap=True,
                source=ctx.providers.CartoDB.Positron,

                # interactive plot config
                tiles='OpenStreetMap',
                zoom_start=12,
                control_scale=True,

                # others
                title="",
                filepath=None,

                # callback: Callable[[Fig, Axes], None]
                # get's passed fig, ax
                callback=None,
            )
        
        # update dict with user supplied keyword arguments
        self.update(**kwargs)

        self.gen = ['color', 'alpha']
        if add_keys:
            self.gen = self.gen + list(kwargs.keys())

    def update(self, **kwargs):
        """update plot keyword arguments
        """
        for key, val in dict(**kwargs).items():
            self[key] = val

    def from_keys(self, keys: Sequence) -> dict:
        """extract dict from plot keyword args based on a sequence of keys

        Args:
            keys: (set | list): keys to extract from dict
        """
        return {k: v for k, v in self.items() if k in keys}

    def lines(self, **kwargs) -> dict:
        """get keyword arguments for plotting point/polygon geomtries

        """
        self.update(**kwargs)
        keys = set(self.gen + ['linewidth', 'linestyle'] + list(kwargs.keys()))
        return self.from_keys(keys)

    def points(self, **kwargs) -> dict:
        """get keyword arguments for plotting line geometries

        """
        self.update(**kwargs)
        keys = set(self.gen + ['marker', 'markersize'] + list(kwargs.keys()))
        return self.from_keys(keys)

    def interactive(self, **kwargs) -> dict:
        """get keyword arguments for interactive plots

        """
        self.update(**kwargs)
        keys = set(['tiles', 'zoom_start', 'control_scale'] + list(kwargs.keys()))
        return self.from_keys(keys)

    def static(self, **kwargs) -> dict:
        """get keyword arguments for static plots

        """
        self.update(**kwargs)
        keys = set(['source'] + list(kwargs.keys()))
        return self.from_keys(keys)

    def kwargs(self, geodata: geopandas.GeoDataFrame, **kwargs) -> dict:
        """get keyword arguments based on the geometry type of geodata

        Args:
            geodata (geopandas.GeoDataFrame): geodataframe
            kwargs: keyword arguments to pass to plot function
        """
        gtypes = ' '.join(list(geodata.geometry.geom_type.unique())).lower()
        if 'point' in gtypes or 'polygon' in gtypes:
            return self.points(**kwargs)
        elif 'line' in gtypes:
            return self.lines(**kwargs)
