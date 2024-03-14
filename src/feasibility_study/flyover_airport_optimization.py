from typing import List

from src.projects.electric_airliner.flight_path_generation import AirportLocation

def optimize_flyover_airports(
    airport_a: AirportLocation, airport_b: AirportLocation
) -> List[AirportLocation]:
    ...
    # draw line from a to b
    # if soc drops below thres, find nearest airport to AB
    #     what if too late or too soon?
    # alternative:
    #     1. find ~~location~~ distance where soc drops below thres
    #     2. find closest airport to original flight path within radius of said distance
