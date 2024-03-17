The Mid-Air Refueling Scheme
============================

The airliner would be recharged by one or more UAVs over the course of its flight from origin airport to destination airport.

To facilitate the operations required to store, maintain, refuel, recharge, launch, and monitor these UAVs, the UAVs would most practically operate out of international airports between the origin and destination. The UAVs would share the same kind of provisions and services used by airliners operating out of these intermediate airports (hangars, refueling equipment, runways, and air traffic control), but would most practically be owned by the airport and shared between airlines rather than owned by separate airlines. Such intermediate airports and their services would be expanded as necessary to operate the UAVs. Airliners would be charged for their use of UAV operations.

Whether to alter the airliner's flight path to meet the UAV(s) over their intermediate airports (option A) or to alter each UAV's flight path to meet the airliner (option B) would require an analysis factoring in the locations of the airports involved and the burn rate of the fuel (or whichever energy storage medium) per distance traveled of the UAV(s) versus that of the airliner. Moreover, determining an optimal compromise between options A and B would require solving an optimization problem for each airliner flight path given its UAV(s).

However, the most important factor is safety, in whose consideration option A---in which airliners fly in the airspace of intermediate airport(s) to be recharged by UAV(s)---is most viable. Although the UAV(s) are uncrewed, if there is a problem surrounding the recharging process, the airliner can safely land at the intermediate airport. Thus, Option A is assumed both for this study and for the 3D computer simulation.

The desire for the aforementioned backup plan in case of an emergency has implications on precisely when, where, and how in the intermediate airport's airspace the airliner would be recharged. For maximum safety, the airliner would likely be recharged in the intermediate airport's airspace while flying towards rather than from the airport to avoid having to circle back to it before landing in case of an emergency during recharging. However, this likelihood and the exact flight path taken by the airliner through the airport's airspace would depend on the configuration of the airport's runways and would be computed for each airliner flight path given its UAV(s). For this study, in line with its inherent simplifications, it is assumed that the airliner is recharged to its new SoC instantly upon flying directly over the intermediate airport. For the 3D computer simulation, it is assumed that the airliner flies directly over the intermediate airport, with the exception of any curve in its flight path as it does so, and the airliner is recharged as it flies towards the airport and possibly as it flies away from it as well.

Each UAV would be fueled, and its battery charged, by its airport services. Each UAV would autonomously follow each stage of the following flight plan and UAV sequence:

1. Taxi, takeoff, and climb.
2. Navigate to and intercept with the airliner's flight path.
3. Dock with the airliner, charge the airliner, and undock.
4. Clear the airliner and navigate back to its originating airport.
5. Descend, land, and taxi.
