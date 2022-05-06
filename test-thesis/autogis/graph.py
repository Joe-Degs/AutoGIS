from typing import Callable, Optional
from typing_extensions import Self
from shapely.geometry import Polygon
import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt

from .utils import *
from .route import *

class Graph:
    
    def __init__(self, graph_from: str, opt_arg=None):
        # from_bbox=False,
        # from_place=False,
        # from_address=False,
        # from_polygon=False,
        # from_point=False,
        # custom_download=False, func=None,
        # coord_with_distance=False,
        # address_with_distance=None,
        # place_names=None):
        
       
        # downloader downloads the graph 
        self.downloader: Optional[Callable[..., nx.MultiDiGraph]] = None

        match graph_from: 
            case 'bbox':
                self.downloader = ox.graph_from_bbox
            case 'address':
                self.downloader = ox.graph_from_address
            case 'place':
                self.downloader = ox.graph_from_place
            case 'point':
                self.downloader = ox.graph_from_point
            case 'polygon':
                self.downloader = ox.graph_from_polygon
            case 'route':
                # get graph from a route object
                self.downloader = opt_arg
            case 'custom':
                self.downloader = opt_arg

        # G is a networkx.MultiDiGraph that osmnx produces
        self.G: nx.MultiDiGraph | None = None
        
        # nodes in the graph
        self.N: geopandas.GeoDataFrame | None = None
        
        # edges in the graph
        self.E: geopandas.GeoDataFrame | None = None
        
        Geometry = dict[str, geopandas.GeoDataFrame]
        self.geometries: Geometry = dict()
        
        # boolean value to represent is graph is projected
        self._projected = False
        
        #TODO: shortest path analysis and gathering of stats
        # present this work by next week to TAs and get a lecturer
        # to start guiding me on what to do next.
        # download geometries in the graph extent and optionally
        # provide parameters to plot functions to plot them
        
    def graph(self, *args, **kwargs) -> nx.MultiDiGraph:
        """get networkx.MultiDiGraph downloaded by osmnx

        Returns:
            networkx.MultiDiGraph: graph downloaded by osmnx
        """
        if self.G is None:
            self.G = self.downloader(*args, **kwargs)
        return self.G

    def download(self, *args, **kwargs) -> Self:
        """download street network graph from openstreetmap using osmnx

        Returns:
            Self@Graph: object of graph
        """
        self.graph(*args, **kwargs)
        return self

    def project(self, crs=None) -> Self:
        """reproject graph to UTM zone if crs is None
        
        it projects to the UTM Zone in which the center
        of the graph lies

        Args:
            crs (pyproj.CRS | str, optional): crs to project from. Defaults to None.

        Returns:
            Self@Graph: object of Graph
        """
        if not self._projected:
            self.G = ox.project_graph(self.graph(), to_crs=crs)
            self.N, self.E = ox.graph_to_gdfs(self.graph())
            self._projected = True
        return self
    
    def nodes(self) -> Self:
        """get nodes/intersection of streets from graph

        Returns:
            Self@Graph: self.G
        """
        if self.N is None:
            self.N = ox.graph_to_gdfs(self.graph(), nodes=True, edges=False)
        return self
    
    def edges(self) -> Self:
        """get edges from the multidigraph `G`

        Returns:
            Self@Graph: returns the Graph object
        """
        if self.E is None:
            self.E = ox.graph_to_gdfs(self.graph(), nodes=False, edges=True)
        return self
    
    def nodes_and_edges(self) -> Self:
        """get nodes and edges from graph

        Returns:
            Self@Graph: object of graph
        """
        return self.nodes().edges()
    
    def get_crs(self):
        return self.nodes().N.crs
    
    def polygon(self) -> Polygon:
        self.nodes().N.unary_union.convex_hull
    
    def point_geometry(self, key: str, tags: dict, dist=1000) -> Self:
        """download geometries in the extent of the graph
        
        see osmnx.graph.geometries_from_point docs for more

        Args:
            key (str):   unique key describing OSM entity
            tags (dict): tags to pass to osmnx function
            dist (int | float):  distance in meters

        Returns:
            Self: object of graph
        """
        if not key in self.geometries:
            c = self.polygon().centroid
            self.geometries[key] = to_crs(self.get_crs(),
                                        ox.geometries_from_point((c.y, c.x), tags, dist=dist))
        return self
    
    def polygon_geometry(self, key: str, tags: dict) -> Self:
        """create a geodataframe of OSM entities with (multi)polygon

        Args:
            key (str): unique key describing OSM entity
            tags (dict): tags to pass to osmnx function

        Returns:
            Self: graph
        """
        if not key in self.geometries:
            self.geometries[key] = to_crs(self.get_crs(),
                                        ox.geometries_from_polygon(self.polygon(), tags))
        return self

    def plot(self, graph=None):
        """plot uses the osmnx.plot_graph method to do exploratory plot
        of the graph. It recieves an optional `graph` parameter to plot
        instead of the one associated with the object.
        
        Parameter
        ---------
        graph: networkx.MultiDiGraph
        """
        return ox.plot_graph(graph or self.graph())
    
    def __get_fig_ax(self, args: dict):
        return plt.subplots(nrows=args['nrows'],
                          ncols=args['ncols'],
                          figsize=args['figsize'])
    
    
    def static_plot(self, **plot_kwargs):
        """

        Returns:
            pyplot.Figure, pyplot.Axes: return the figure and axis
        """
        args = plot_args(**plot_kwargs)
        fig, ax = self.__get_fig_ax(args)
        # TODO: ax could be anything depending on nrows, ncols.. check that!
        
        # plot edges in network
        if args['nodes']:
            # TODO: make args['markersize'] changeable
            self.nodes().N.plot(ax=ax, color=args['node_color'],
                           alpha=args['node_alpha'],
                           markersize=args['node_size'])
        
        # plot the edges in graph / street network
        if args['edges']:
            self.edges().E.plot(ax=ax, color=args['line_color'],
                   linewidth=args['linewidth'],
                    alpha=args['line_alpha'])
        
        # plot the axis
        if not args['axis']:
            ax.axis('off') 
        if args['title']:
            ax.set_title(args['title'])
        if args['tight_layout']:
            plt.tight_layout()
        
        # add basemap
        if args['tiles'] and (crs := self.get_crs()) is not None:
                ctx.add_basemap(ax, crs=crs, source=args['static_tile'])
        
        # save the resulting plot
        if args['filepath'] is not None:
            plt.savefig(args['filepath'])
        
        plt.show()
        return fig, ax

    def interactive_plot(self, *args, **kwargs):
        """do an interactive plot of the map
        """
        args = plot_args(*args, **kwargs)
        return args