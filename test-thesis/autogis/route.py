import random
import folium
import pandas
import geopandas

from .utils import *

class Route():
    """route allows you to load a point or bunch of them
    
    this allows you to do shortest path analysis and plot them
    on a bigger graph
    """
    
    def __init__(self, point_type, origin, destination):
        """
        NB: [origin/destination]_point can be a
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
                1. csv_coords (x, y) points || csv_names (names to geocode)
                2. coords || coords_list
            should be loaded

        origin : str | tuple[float, float] | list[tuple[float, float]]
            points of origin for shortest path analysis
        destination : str | tuple[float, float] | list[tuple[float, float]]
            destination points for shortest path analysis
        """
        
        self.origin: None | pandas.DataFrame = None
        self.destination: None | pandas.DataFrame = None
        self.origin_geo: None | geopandas.GeoDataFrame = None
        self.destination_geo: None | geopandas.GeoDataFrame = None
        self.all_points: None | pandas.DataFrame = None
        self.all_points_geo: None | pandas.DataFrame = None
        
        typ = point_type.split('_')
        assert len(typ) >= 1, "Route: invalid point_type"
        if typ[0] == 'csv':
            self.origin, self.destination = load_csv(',', origin, destination)
        elif typ[0] == 'coords':
            
            # if coordinates is not list, convert to list
            if type(origin) == tuple:
                origin = [origin]
                destination = [destination]
                
                print(self.origin, self.destination)
                
            self.origin = pandas.DataFrame(origin, columns=['y', 'x'])
            self.destination = pandas.DataFrame(destination, columns=['y', 'x'])
        
        # do the geocode
        if 'coords' in point_type:
            self.origin_geo, self.destination_geo = reverse_geocode_all(
                coords_from_df(self.origin), coords_from_df(self.destination))
        elif 'name' in point_type:
            # geocode names to points or polygons
            pass
        
    def to_crs(self, crs):
        "convert origin/destination geodata to new CRS"
        self.origin_geo.to_crs(crs, inplace=True)
        self.destination_geo.to_crs(crs, inplace=True)
        return
    
    # def all_points(self):
    #     """concatenate pandas dataframe of origin and destination points
    #     """
    #     # if self.all_points is None:
    #     #     self.all_points = join = \
    #     #         pandas.concat([self.origin, self.destination], axis=0, ignore_index=True)
    #     return \
    #         (self.all_points := \
    #             pandas.concat([self.origin, self.destination], axis=0, ignore_index=True)) \
    #                 if self.all_points is None else self.all_points
        
    def geodata(self) -> geopandas.GeoDataFrame:
        """geodata makes a geodataframe of geocoded origin/destination
        """
        if self.all_points_geo is None:
            self.all_points_geo = self.origin_geo.append(self.destination_geo)
            self.all_points_geo.reset_index(inplace=True)
        return self.all_points_geo

    def head(self):
        "return head of pandas dataframe"
        return self.origin, self.destination
    
    def head_geo(self) -> tuple[geopandas.GeoDataFrame, geopandas.GeoDataFrame]:
        """return head of geodataframe"""
        return self.origin_geo, self.destination_geo
    
    def get_extent(self):
        """get a poygon specifying the extent of the route points
        it is buffered a little bit to contain important adjoining
        streets that might be cut off otherwise
        """
        return self.geodata().unary_union.convex_hull.buffer(0.1)
    
    def explore(self, **kwargs) -> folium.Map:
        """do interactive plot to explore origin/destination points
        """
        geodata = self.geodata()
        coords = [[p.y, p.x] for p in geodata.geometry]
        map = folium.Map(location=random.choice(coords), tiles='OpenStreetMap', 
            zoom_start=12, control_scale=True)
        # add markers for the name of each location added to map
        for i, coord in enumerate(coords):
            map.add_child(
                folium.Marker(location=coord, popup=str(geodata.address[i]),
                              icon=folium.Icon(color='green', icon='ok-sign'))
            )

        if kwargs['filepath'] is not None:
            map.save(kwargs['filepath'])

        return map