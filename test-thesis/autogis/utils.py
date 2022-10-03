import os
from typing import Sequence
import geopandas
import pandas

import matplotlib.colors as colors
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import contextily as ctx
from pyproj import CRS
import osmnx as ox
import networkx as nx
from shapely.geometry import Point

def load_csv(sep: str, *files: str, **kwargs) -> list[pandas.DataFrame]:
    """load csv file from filesystem"""
    assert len(files) == 2, "load_csv: expecting two files"
    assert all([os.path.isfile(f) for f in files]), \
        "load_csv: arguments must be valid csv files"
    return [pandas.read_csv(file, sep=sep or ',', **kwargs) \
        for file in files]
    
def calc_bbox(center: tuple|Point, distance: int):
    """calculate bounding box of length distance around center point
    
    the formulae used here will not work well for regions along the poles

    Args:
        center (tuple | Point): a tuple of (lat, long) coordinates or a shapely point
        distance (int): distance(in meters) from point to construct center point
    
    Returns:
        tuple(float): coordinates in the format north, south, east, west
    """
    lat, lon = 0.0, 0.0
    if type(center) is Point:
        lat, lon = center.y, center.x
    elif type(center) is tuple:
        lat, lon = center
    else:
        raise Exception(f"expected tuple or shapely point, got {str(type(Point))}")
    off = (distance * 0.001) / 111
    lat_max = lat + off
    lat_min = lat - off 
    lon_max = lon + off
    lon_min = lon - off 
    return lat_max, lat_min, lon_max, lon_min

def get_graph_area(G: nx.MultiDiGraph):
    """return area of graph in meters

    Args:
        G (nx.MultiDiGraph): _description_

    Returns:
        _type_: _description_
    """
    nodes = ox.graph_to_gdfs(ox.project_graph(G), edges=False)
    return nodes.unary_union.convex_hull.area

def download_center_distance(center: tuple|Point, area: int, network_type: str = 'drive') -> nx.MultiDiGraph:
    """download street network graph of given point with rectangular bbox
    
    Args:
        center (tuple | Point): a tuple of (lat, long) coordinates or a shapely point
        area (int): distance(in meters) from point to construct center point
    """
    n, s, e, w = calc_bbox(center, area)
    return ox.graph_from_bbox(n, s, e, w, network_type=network_type)

def black_bg_plot(G: nx.MultiDiGraph, **kwargs):
    """plot black street network graph on white background
    
    Returns:
        fig, ax: matplotib figure and axes objects
    """
    return ox.plot_graph(
        G,
        figsize=(10, 10),  # figure size to create if ax is None
        bgcolor="w",  # background color of the plot
        node_color="black",  # color of the nodes
        node_size=20,  # size of the nodes: if 0, skip plotting them
        edge_color="black",  # color of the edges
        edge_linewidth=1.5,  # width of the edges: if 0, skip plotting them
        show=False,
        **kwargs)
    
def visualize_edge_cc(G: nx.MultiDiGraph, **kwargs):
    """calculate and plot centrality for each street in the graph
    the color map depicts the most central streets in bright yellow
    and least central in dark purple
    
    Returns:
        fig, ax: matplotib figure and axes objects
    """
    edge_centrality = nx.closeness_centrality(nx.line_graph(G))
    ev = [edge_centrality[edge + (0,)] for edge in G.edges()]
    norm = colors.Normalize(vmin=min(ev)*0.8, vmax=max(ev))
    cmap = cm.ScalarMappable(norm=norm, cmap=cm.inferno)
    ec = [cmap.to_rgba(cl) for cl in ev]
    return ox.plot_graph(
        G,
        bgcolor='white',
        figsize=(10, 10),
        node_size=0,
        edge_color=ec,
        edge_linewidth=2,
        edge_alpha=1,
        show=False,
        **kwargs)

def visualize_edge_bc(G: nx.MultiDiGraph, **kwargs):
    """visualize the betweenness centrality of street segments

    the color map depicts the most central streets in bright yellow
    and least central in dark purple
    
    returns:
        fig, ax: matplotib figure and axes objects
    """
    bc = nx.edge_betweenness(G, normalized=True)
    ev = [i[0] + (0,) for i in bc.items()]
    for i, j in zip(ev, bc.keys()):
        bc[i] = bc[j]
        del bc[j]
    norm = colors.Normalize(vmin=min(bc.values())*0.8, vmax=max(bc.values()))
    cmap = cm.ScalarMappable(norm=norm, cmap=cm.inferno)
    ec = [cmap.to_rgba(cl) for cl in bc.values()]
    return ox.plot_graph(
        G,
        bgcolor='white',
        figsize=(10, 10),
        node_size=0,
        edge_color=ec,
        edge_linewidth=2,
        edge_alpha=1,
        show=False,
        **kwargs)

def clean_heights(x):
    try:
        return float(x)
    except ValueError:
        return 0

def building_footprint_from_graph(path: str, dist=700):
    """given the path to the graph, download and save the building footprint of
    the graph
    """
    G = ox.load_graphml(f"{path}.graphml")
    nodes = ox.graph_to_gdfs(ox.project_graph(G), edges=False)
    center = nodes.unary_union.convex_hull.centroid
    lat, lng = center.y, center.x
    print(lat, lng)
    gdf = None
    file = f"{path}.geojson"
    if not os.path.exists(file):
        gdf = ox.geometries_from_point((lat,lng), dist=dist, tags={'building': True})
        gdf.to_file(file, driver="GeoJSON")
    else:
        gdf = geopandas.read_file(file)
    buildings = ox.projection.project_gdf(gdf)
    buildings = buildings[buildings.geom_type.isin(['Polygon', 'MultiPolygon'])]
    buildings['height'] = buildings['height'].fillna(0).apply(clean_heights)
    buildings = buildings.reset_index().explode()
    buildings.reset_index(inplace=True, drop=True)
    return buildings

def visualize_street_footprint(path: str, **kwargs):
    """visualize the building footprints of study area
    """
    G = ox.load_graphml(f"{path}.graphml")
    G = ox.projection.project_graph(G)
    edges = ox.graph_to_gdfs(G, nodes=False, edges=True, node_geometry=False,
            fill_edge_geometry=True)
    buildings = building_footprint_from_graph(path)
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    buildings.plot(ax=ax, color='darkgrey')
    edges.plot(ax=ax)
    ax.set_axis_off()
    return fig, ax

def visualize_street_profile(path: str, **kwargs):
    """

    """
    pass

def visualize_node_length(G: nx.MultiDiGraph, **kwargs):
    """colormap of nodes based on their attributes

    Args:
        G (nx.MultiDiGraph): street network graph
    
    Returns:
        fig, ax: matplotib figure and axes objects
    """
    nc = ox.plot.get_node_colors_by_attr(G, 'y', cmap='inferno')
    return ox.plot_graph(
        G,
        figsize=(10, 10),
        bgcolor='white',
        node_size=20,
        node_color=nc,
        edge_color='black',
        edge_linewidth=0.3,
        show=False,
        **kwargs)

def visualize_node_bc(G: nx.MultiDiGraph, **kwargs):
    """calculate and plot betweeness centrality of nodes on the directed graph
    of the downloaded multigraph 

    Args:
        G (nx.MultiDiGraph): street network downloaded and constructed by osmnx
    
    Returns:
        fig, ax: matplotib figure and axes objects
    """
    bc = nx.betweenness_centrality(ox.get_digraph(G), weight='length')
    nx.set_node_attributes(G, bc, 'bc')
    nc = ox.plot.get_node_colors_by_attr(G, 'bc', cmap='inferno')
    return ox.plot_graph(
        G,
        figsize=(10, 10),
        bgcolor='white',
        node_color=nc,
        node_size=50,
        node_zorder=2,
        edge_color='black',
        edge_linewidth=0.3,
        show=False,
        **kwargs)

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

def lat_long_from_coords(coords: list[tuple]):
    """given a list of coordinates [ len(tuple)==2 ] extract first
    values as lattitude and second values a longitudes values
    """
    x, y = list(zip(*coords))[0], list(zip(*coords))[1]
    return list(x), list(y)


def nearest_node_ids(G: nx.MultiDiGraph, longitude: list[float],
        lattitude: list[float]) -> list[str]:
    """get the id's of nearest nodes around some coordinates in a
    graph
    """
    return ox.nearest_nodes(G, longitude, lattitude)

def select_from(data: geopandas.GeoDataFrame, ids: list[str]):
    """return a geopandas or geoseries selected from nodes based on
    node ids
    """
    return data.loc[ids]

def concat_ids(*ids: list[str]) -> list[str]:
    """concatenate list of ids

    Returns:
        list[str]: _description_
    """
    return list(set(*ids))
    

def to_crs(crs: CRS | str, data: geopandas.GeoDataFrame) \
    -> geopandas.GeoDataFrame:
    """convert data to new CRS

    Returns:
        geopandas.GeoDataFrame: changed data
    """
    return data.to_crs(crs) if data.crs != crs \
        else data

def unhashable_cols(data: geopandas.GeoDataFrame) -> list[str]:
    """return the names of all columns with unhashable types
    
    this is to stop the error: unhashable type: 'list'
    geometry columns are excluded
    """
    cols_stat = list((data.applymap(type) == list).any().items())
    return [c for c, h in cols_stat if h and c != 'geometry']

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
                markersize=10,
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
            self.gen = list(set(self.gen + list(kwargs.keys())))

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
