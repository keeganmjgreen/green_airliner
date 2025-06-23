.. _airliner_uav_selection:

Selection of the Commercial Airliner and UAV
============================================

Selection of the Commercial Airliner
------------------------------------

An Airbus A320ceo is selected for this study because it is one of the most used models---if not *the* most-used model---of commercial airliner today. It is of reasonably large size. It has a similar design to other commercial airliners of similar size whose use is widespread, making this study applicable or more easily adapted to those other models of commercial airliner.

Specifications of the Airbus A320ceo are as follows::

    Parameter                                           Value
    ―――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    Cruise speed                                     829 km/h
    Fuel consumption rate at cruise         2,430 kg/h jet A1
                                            3,020  L/h jet A1
                                       105,000 MJ/h = 29.2 MW
    Fuel capacity                                    27,200 L
                                            944,000 MJ jet A1
    Assumed fuel volume capacity                    21,900 kg
    Turbofan efficiency                                   69%

The A320ceo burns over 3000 L of jet A1 fuel for every hour in cruise, of 11% of its capacity. Another perspective on how large the quantity of energy consumed by airliners such as the A320ceo is the fact that it expends 29.2 MW at cruise, which is comparable to the power capacities (notably greater than typical generation levels) of:

- More than two of the world's largest commercially deployed wind turbine as of 2024 (13 MW, offshore).
- The Monte Plata solar farm in the Dominican Republic, the largest PV plant in the Caribbean (30 MW).

Converting the fuel consumption rate to power in MW also makes clear the challenge of mid-air refueling if this takes the form of delivering electrical power (such as to recharge onboard batteries) as opposed to a fuel of high energy density. The largest electrical charging connector under development as of 2024 is the Megawatt Charging System (MCS) which delivers up to 3.75 MW. This simply does not compare to the 30 MW consumption rate; eight MCS connectors in parallel would be required.

Selection of the UAV
--------------------

Selection of the secondary aircraft to be used to refuel the commercial airliner is complex. Considerations include size, control, energy source, etc. Notably, many of these considerations also apply to the commercial airliner.

**Size of the secondary aircraft.** The secondary aircraft was selected to be a small aircraft because it is intended to carry the space and weight of enough of the energy storage medium to refuel (partially or fully) *one* commercial airliner per flight of the secondary aircraft, as opposed to multiple. Refueling multiple commercial airliners for each of its flights would require fewer take-offs and landings of the secondary aircraft, but would require the secondary aircraft to be larger to carry multiple refuelings' worth of energy, meaning that it is inefficient to stay airborne and likely not worthwhile. Calculations will especially determine whether the TODO

**Control of the secondary aircraft.** An uncrewed aerial vehicle (UAV) aircraft was selected because, in autonomous mode of operation, it can be safer without human error. Furthermore, it is smaller and lighter than its crewed counterpart, leaving more space and weight capacity for any cargo, which in our case is the energy storage medium and any equipment required for mid-air refueling. In future sections, the secondary aircraft will be referred to as the UAV. Notably, the size of UAV selected is not to be confused with much smaller "drones" which serve very different purposes; even heavy-lift drones are insufficient.

**Energy source of the secondary aircraft.** Although many UAVs are electric and the goal for which this study is done is the reduction of air travel GHG emissions using electric commercial airliners, the UAV does not need to be electric. On the contrary, assuming a UAV powered by aviation gasoline will more readily and realistically allow it to support an electric commercial airliner by being able to carry more energy and farther. Thus, the commercial airliner makes most of the GHG reductions by design; the benefits likely outweigh the drawback of a GHG-emitting UAV.

The UAV selected is the AT200 cargo UAV, which was developed in 2017 in collaboration between the Institute of Engineering Thermophysics of China and China's *Longwing UAV Systems* aircraft manufacturer. The AT200 was not designed and built from scratch, however; it is based on the PAC-750 XL turboprop light utility aircraft developed by New Zealand's *Pacific Aerospace* aircraft manufacturer.

Specifications of the PAC-750 XL (and thus of the AT200) are as follows::

    Parameter                     Value
    ―――――――――――――――――――――――――――――――――――
    Payload capacity           1,500 kg
    Payload volume      5 m³ or 5,000 L
