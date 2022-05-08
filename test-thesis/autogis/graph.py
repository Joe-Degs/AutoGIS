from typing import Callable, Optional
from typing_extensions import Self
from shapely.geometry import Polygon
import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt

from .utils import *
from .route import *

class Graph:
    
    def __init__(self, graph_from: str, opt_arg:Optional[Callable]=None):

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
                # get graph from origins(s)/destination(s) points
                self.downloader = opt_arg.graph
            case 'custom':
                self.downloader = opt_arg

        # G is a networkx.MultiDiGraph that osmnx produces
        self.G: Optional[nx.MultiDiGraph] = None
        
        # nodes in the graph
        self.N: Optional[geopandas.GeoDataFrame] = None
        
        # edges in the graph
        self.E: Optional[geopandas.GeoDataFrame] = None
       
        # extra OSM entities in the extent of the graph
        # The Geometry type represents a plottable geometry
        # the dict holds the arguments to pass to the `plot`
        # function
        # TODO(Joe-Degs): change self.geometries to represent
        # this.
        Geometry = tuple[geopandas.GeoDataFrame, dict]
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
        self.edges().E.unary_union.convex_hull


    def __add_geometry(self, key, geom, **kwargs):
        """add new geometry to list of geomtries
        """
        self.geometries[key] = (geom, PlotArgs(**kwargs).kwargs(geom))
        return


    def geometry_from_point(self, key: str, tags: dict, dist=1000, **kwargs) -> Self:
        """create geodataframe of OSM entities with shapely point
        
        it uses the center of the graph with the distance and tags of
        geometries to query for on OSM and downloads those geometries.
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
            geom = to_crs(self.get_crs(),
                    ox.geometries_from_point((c.y, c.x), tags, dist=dist))
            self.__add_geometry(key, geom, **kwargs)
        return self

    def geometry_from_polygon(self, key: str, tags: dict, **kwargs) -> Self:
        """create geodataframe of OSM entities with (multi)polygon

        it uses the center of the graph with the distance and tags of
        geometries to query for on OSM and downloads those geometries.
        see osmnx.graph.geometries_from_point docs for more

        Args:
            key (str): unique key describing OSM entity
            tags (dict): tags to pass to osmnx function
            kwargs (): keyword argumnents to pass to plot funtions

        Returns:
            Self: graph
        """
        if not key in self.geometries:
            geom = to_crs(self.get_crs(),
                    ox.geometries_from_polygon(self.polygon(), tags))
            self.__add_geometry(key, geom, **kwargs)
        return self

    # TODO(Joe-Degs): do the add_routes function on routes
    def add_route(route: Route, **kwargs) -> Self:
        """add origin/dest points and get shortest path between points

        this route(s) can be plotted, used for shortest path analysis
        and other types network analysis in the graph

        Args:
            route (Route): route of origin/destination point(s)
            kwargs: keyword args to pass to `plot` function
        """
        self.projected().nodes_and_edges()
        # route.shortest_paths(self.N, self.E)
        # args = plot_args(**plt_args):
        # self.routes.append((route, args))
        return self

    def plot(self, graph: Optional[nx.MultiDiGraph]=None):
        """plot uses the osmnx.plot_graph method to do exploratory plot
        of the graph. It recieves an optional `graph` parameter to plot
        instead of the one associated with the object.
        
        Parameter
        ---------
        graph: networkx.MultiDiGraph
        """
        return ox.plot_graph(graph or self.graph())
   
    # TODO(Joe-Degs): take care of this shit, this whole code is
    # gross, but this shit is way too gross. remove it, make it
    # betterrrrr!
    def __get_fig_ax(self, args):
        return plt.subplots(nrows=args['nrows'],
                          ncols=args['ncols'],
                          figsize=args['figsize'])
    
    
    def static_plot(self, lines: dict, points: dict, **kwargs):
        """

        Returns:
            pyplot.Figure, pyplot.Axes: return the figure and axis
        """
        args = PlotArgs(add_keys=False, **kwargs)
        fig, ax = self.__get_fig_ax(args)
        # TODO: ax could be anything depending on nrows, ncols.. check that!
        
        # plot edges in network
        if args['nodes']:
            self.nodes().N.plot(ax=ax, **args.points(alpha=None, **points))
        
        # plot the edges in graph / street network
        if args['edges']:
            self.edges().E.plot(ax=ax, **args.lines(**lines))
        
        # plot the axis
        if not args['axis']:
            ax.axis('off') 
        if args['title']:
            ax.set_title(args['title'])
        if args['tight_layout']:
            plt.tight_layout()
        
        # add basemap
        if args['basemap'] and (crs := self.get_crs()) is not None:
                ctx.add_basemap(ax, crs=crs, **args.static())
        
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
