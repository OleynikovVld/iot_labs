import asyncio
import math
from kivy.app import App
from kivy_garden.mapview import MapMarker, MapView
from kivy.clock import Clock
from lineMapLayer import LineMapLayer
from datasource import Datasource, ProcessedAgentData
import logging
import uuid
from typing import List, Tuple
from time import sleep

logger = logging.getLogger()


class MapViewApp(App):
    def __init__(self, **kwargs):
        super().__init__()
        # додати необхідні змінні
        self.mapview = None
        self.car_marker = None
        self.map_layer = None
        # Init data source
        self.datasource = Datasource(user_id=str(uuid.uuid4()))

    def on_start(self):
        """
        Встановлює необхідні маркери, викликає функцію для оновлення мапи
        """
        # We're assuming, that we don't have any information on boot
        # So we just update map
        Clock.schedule_interval(self.update, 1)

    def on_stop(self):
        self.datasource.close()

    def update(self, *args):
        """
        Викликається регулярно для оновлення мапи
        """
        # Refresh data source information
        new_points = self.refresh_datasource()
        # logger.info(f"Received points: {new_points}")
        if len(new_points) == 0:
            return
        for value in new_points:
            point = (value[1], value[0])
            self.map_layer.add_point(point)

        if new_points[-1][2] == "small pits":
            self.set_bump_marker(point)
        elif new_points[-1][2] == "large pits":
            self.set_pothole_marker(point)
        self.update_car_marker(new_points[-1])

    def refresh_datasource(self):
        # Trigger get_new_points
        return self.datasource.get_new_points()

    def add_marker(self, lat, lon, source):
        marker = MapMarker(lat=lat, lon=lon, source=source)
        self.mapview.add_marker(marker)

    def update_car_marker(self, point: Tuple[float, float]):
        """
        Оновлює відображення маркера машини на мапі
        :param point: GPS координати
        """
        self.mapview.remove_marker(self.car_marker)
        self.car_marker.lat = point[1]
        self.car_marker.lon = point[0]
        self.mapview.add_marker(self.car_marker)

    def set_pothole_marker(self, point: Tuple[float, float]):
        """
        Встановлює маркер для ями
        :param point: GPS координати
        """
        pothole = MapMarker(lat=point[0], lon=point[1], source="images/pothole.png")
        self.mapview.add_marker(pothole)
        pass

    def set_bump_marker(self, point: Tuple[float, float]):
        """
        Встановлює маркер для лежачого поліцейського
        :param point: GPS координати
        """
        bump = MapMarker(lat=point[0], lon=point[1], source="images/bump.png")
        self.mapview.add_marker(bump)
        pass

    def build(self):
        """
        Ініціалізує мапу MapView(zoom, lat, lon)
        :return: мапу
        """
        self.map_layer = LineMapLayer()
        self.mapview = MapView(
            zoom=15,
            lat=50.4501,
            lon=30.5234,
        )
        self.mapview.add_layer(self.map_layer, mode="scatter")
        self.car_marker = MapMarker(
            lat=50.45034509664691,
            lon=30.5246114730835,
            source="images/car.png",
        )
        self.mapview.add_marker(self.car_marker)
        return self.mapview


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(MapViewApp().async_run(async_lib="asyncio"))
    loop.close()
