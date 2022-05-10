from typing import Callable, Optional
from typing_extensions import Self
from shapely.geometry import Polygon
import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt

from .utils import *
from .route import *

class Graph:
    """Graph provides basic functionality for downloading street networks as
    directed graph's from Open Street Map using the osmnx library
    """
    
    def __init__(self, graph_from: str, opt_arg:Optional[Callable]=None):
        """
        Args:
            graph_from (str): options to customize the method/function for
            downloading the street network graph. available options are;
                * 'bbox' : use osmnx.graph_from_bbox function
                * 'address' : use osmnx.graph_from_address function
                * 'place' : use osmnx.graph_from_place function
                * 'polygon' : use osmnx.graph_from_polygon function
                * 'point' : use osmnx.graph_from_point function
                * 'route' : get graph from `Route` object
                * 'custom' : pass custom function in opt_arg parameter

            opt_arg (Optional[Callable], optional): Defaults to None.
        """
       
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
        # the dict holds the arguments to pass to plot
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
        """get street network lines from graph

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
    
    def crs(self):
        """get CRS of the graph
        """
        return self.nodes().N.crs
    
    def extent(self) -> Polygon:
        """get entire area that graph covers as a shapely polygon

        Returns:
            Polygon: shapely polygon representing the extent of graph
        """
        self.edges().E.unary_union.convex_hull

    def __add_geometry(self, key: str, geom: geopandas.GeoDataFrame, **kwargs):
        """add new geometry to list of geometries
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
            c = self.extent().centroid
            geom = to_crs(self.crs(),
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
            geom = to_crs(self.crs(),
                    ox.geometries_from_polygon(self.extent(), tags))
            self.__add_geometry(key, geom, **kwargs)
        return self


    # TODO(Joe-Degs): do the add_routes function on routes
    def shortest_path_with_route(self, route: Route, **kwargs) -> Self:
        """add origin/dest points and get shortest path between points

        this route(s) can be plotted, used for shortest path analysis
        and other types network analysis in the graph

        Args:
            route (Route): route of origin/destination point(s)
            kwargs: keyword args to pass to `plot` function
        """
        # project data to same CRS if not already done
        self.projected().nodes_and_edges()
        route.reproject(self.crs())

        # extract coordinates from points
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
    
    
    def static_plot(self, node_kwargs: Optional[dict]={}, \
            edge_kwargs: Optional[dict]={}, **kwargs):
        """generate a static plot of the street network graph

        see `PlotArgs` args on how arguments to plot functions are managed

        Args:
            node_kwargs (dict, optional): keyword arguments to plot nodes
            edge_kwargs (dict, optional): keyword arguments to plot edges
            kwargs: keyword arguments for plotting. see `PlotArgs` for more

        Returns:
            pyplot.Figure, pyplot.Axes: return the figure and axis
        """
        args = PlotArgs(add_keys=False, **kwargs)
        fig, ax = self.__get_fig_ax(args)
        # TODO: ax could be anything depending on nrows, ncols.. check that!
        
        # plot edges in network
        if args['nodes']:
            self.nodes().N.plot(ax=ax,
                    **args.points(alpha=None, **node_kwargs))
        
        # plot the edges in graph / street network
        if args['edges']:
            self.edges().E.plot(ax=ax, **args.lines(**edge_kwargs))
        
        # plot the axis
        if not args['axis']:
            ax.axis('off') 
        if args['title']:
            ax.set_title(args['title'])
        if args['tight_layout']:
            plt.tight_layout()
        
        # add basemap
        if args['basemap'] and (crs := self.crs()) is not None:
                ctx.add_basemap(ax, crs=crs, **args.static())
        
        # save the resulting plot
        if args['filepath'] is not None:
            plt.savefig(args['filepath'])
        
        plt.show()
        return fig, ax

    def interactive_plot(self, **kwargs):
        """do an interactive plot of the map
        """
        args = PlotArgs(add_keys=False, **kwargs).interactive()
        return args
