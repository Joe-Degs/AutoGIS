import random
import folium
import pandas
import geopandas
import networkx as nx
import osmnx as ox
from shapely.geometry import Polygon
from typing import Optional

from .utils import *

class Route():
    """route allows you to load a point or bunch of them
    
    this allows you to do shortest path analysis and plot them
    on a bigger graph
    """
    
    def __init__(self, point_type, origin, dest):
        """
        NB: [origin/destination] point can be a
               1. tupe[float, float] | list[tupe[float, float]] -> (lat, long)
               2. shapely.Point | list[shapely.Point]
               3. geocodable string | list[str]
               4. a csv file of x, y coordinates
               
            coordinates are in the form (lat, long)
                x -> long
                y -> lat
                
        Parameters
        -----------
        point_type : str
            specify how the data of the route
            values:
                1. csv_coords (lat, long) points || csv_address {address(es) to geocode}
                2. coords ([lat, long] values) || coords_list (list of [lat, long] values)
                2. address | sequence of addresses
            should be loaded

        origin : str | tuple[float, float] | list[tuple[float, float]]
            points of origin for shortest path analysis
        destination : str | tuple[float, float] | list[tuple[float, float]]
            destination points for shortest path analysis
        """
        
        self.origin:     Optional[pandas.DataFrame]       = None
        self.dest:       Optional[pandas.DataFrame]       = None
        self.all_data:   Optional[pandas.DataFrame]       = None

        self.origin_geo: Optional[geopandas.GeoDataFrame] = None
        self.dest_geo:   Optional[geopandas.GeoDataFrame] = None
        self.all_geo:    Optional[geopandas.GeoDataFrame] = None
        
        typ = point_type.split('_')
        assert len(typ) >= 1, "Route: invalid point_type"
        if typ[0] == 'csv':
            self.origin, self.dest = load_csv(',', origin, dest)
        elif typ[0] == 'coords':
            
            # if coordinates is not list, convert to list
            if type(origin) is tuple and type(dest) is tuple:
                origin = [origin]
                dest = [dest] 
                # DEBUG 
                print(self.origin, self.dest)
                
            self.origin = pandas.DataFrame(origin, columns=['y', 'x'])
            self.dest = pandas.DataFrame(dest, columns=['y', 'x'])
        
        # do the geocode
        if 'coords' in point_type:
            self.origin_geo, self.dest_geo = reverse_geocode_all(
                coords_from_df(self.origin), coords_from_df(self.dest))

            # get shapely types of geometry column and assert they are
            # all point geometries
            all_types = list(self.origin_geo.geometry.geom_type.unique()) \
                    + list(self.dest_geo.geometry.geom_type.unique())
            assert all('point' in t.lower() for t in all_types), \
                    "origin/destination points must be Point geometries"
        elif 'name' in point_type:
            #TODO(Joe-Degs): add geocode from address functionality
            pass
        
    def to_crs(self, crs):
        "convert origin/destination geodata to new CRS"
        self.origin_geo.to_crs(crs, inplace=True)
        self.dest_geo.to_crs(crs, inplace=True)
        return
    
    def all_points(self) -> pandas.DataFrame:
        """concatenate and return origin/dest points
        """
        if self.all_data is None:
            self.all_data = \
                pandas.concat([self.origin, self.dest], axis=0, ignore_index=True)
        return self.all_data
        
    def geodata(self) -> geopandas.GeoDataFrame:
        """concatenate and return origin/destination geodata
        """
        if self.all_geo is None:
            self.all_geo = self.origin_geo.append(self.dest_geo)
            self.all_geo.reset_index(inplace=True)
        return self.all_geo

    def head(self) -> tuple[pandas.DataFrame]:
        """return head of origin/dest points

        Returns:
            tuple[pandas.DataFrame]: _description_
        """
        return self.origin, self.dest
    
    def head_geo(self) -> tuple[geopandas.GeoDataFrame]:
        """return head of origin/dest geodataframe
        """
        return self.origin_geo, self.dest_geo
    
    def extent(self) -> Polygon:
        """get a poygon specifying the extent of the route points
        it is buffered a little bit to contain important adjoining
        streets that might be cut off otherwise
        """
        return self.geodata().unary_union.convex_hull.buffer(0.01)
    
    def graph(self, **kwargs) -> nx.MultiDiGraph:
        """download the street network graph of the area covering routes

        Returns:
            nx.MultiDiGraph: graph reprenting street network
        """
        return ox.graph_from_polygon(self.extent(), **kwargs)

    def reproject(self, crs: CRS | str):
        """reproject geodata into new CRS

        Args:
            crs (pyproj.CRS | str): crs to project data to
        """
        self.origin_geo = to_crs(crs, self.origin_geo)
        self.dest_geo = to_crs(crs, self.dest_geo)
        self.all_geo = to_crs(crs, self.geodata())
    
    def explore(self, **kwargs) -> folium.Map:
        """do interactive plot to explore origin/destination points
        
        Args:
            **kwargs: keyword args for folium map plotter
        """
        geodata = self.geodata()
        coords = [[p.y, p.x] for p in geodata.geometry]
        map = folium.Map(
                **PlotArgs(location=random.choice(coords)).interactive(**kwargs))
        # add address markers to the map
        for i, coord in enumerate(coords):
            map.add_child(
                folium.Marker(location=coord, popup=str(geodata.address[i]),
                              icon=folium.Icon(color='green', icon='ok-sign'))
            )

        if 'filepath' in kwargs:
            map.save(kwargs['filepath'])

        return map
