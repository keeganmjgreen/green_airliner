Feasibility Studies with Different Energy Storage Media
=======================================================

Given the selected airliner and UAV, studies are performed for different energy storage media to determine whether they can sustain flight and, if so, the number of UAVs required to refuel the airliner at the given airports. The energy storage media include jet A1 (for comparison purposes), liquid hydrogen (LH2), lithium-ion batteries (Li-ion), and lithium-polymer batteries (LiPo). These will often be referred to as "fuels" for simplicity.

The number of UAVs as well as the rate at which each fuel capacity is consumed will also be compared.

First, a real airliner route will be selected as the common scenario in which to run the studies.

Selection of the Airliner Route for Feasibility Studies
-------------------------------------------------------

The airline route from JFK (John F. Kennedy International Airport) to LAX (Los Angeles International Airport) was selected for studies because it is a most frequented airliner route in North America and because it is of reasonable length. Furthermore, it strikes a balance between not flying over too few airports over which to refuel (as in inter-continental flights) and having the luxury of flying over many airports (as in Europe, for example, but cannot be expected globally).

Straight-line distances across the surface of the earth will be assumed for studies. Accordingly, JFK and LAX are approximately 4000 km apart. Neglecting time and energy particular to takeoff, landing, and taxiing, and assuming cruise speed throughout, the selected airline route would take 4 hours 48 minutes and consume 503 GJ of energy, or 53% of the jet A1 capacity of an A320ceo.

The airliner can deviate somewhat from its regular JFK–LAX flight path and fly over relatively nearby airports to be refueled, such as PIT (Pittsburg International Airport) and/or DEN (Denver International Airport). The following table shows the distances, and corresponding durations at A320ceo cruise speed, directly from JFK to LAX versus via detour components through PIT and DEN::

                       Distance (km)    Duration    CO2 Emissions
    ―――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    Before detours:
    JFK–LAX                    3,972       04:47    
    ―――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    Detours:
    JFK-PIT                      544       00:39
    PIT–DEN                    2,070       02:29
    DEN–LAX                    1,384       01:40
    Total: JFK–PIT–DEN–LAX     3,998       04:49

Geographically, a detour over DEN in particular may not be considered negligible, however the total detour only adds 26 km, or 2 minutes, to the total flight time.

Comparisons Between Different Energy Storage Media
--------------------------------------------------

The following table compares the energy densities and densities of fuels and other energy storage media::

    Fuel    Energy Density (MJ/L)     Density (kg/L)    Specific Energy (MJ/kg)
    ―――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    Jet A1                 34.7*     0.804 (at 15°C)                       43.2
    LH2                     8.491    0.07085                              119.8
    Li-ion             0.90–2.49     0.360–0.954        
                      Mean: 1.70     Mean: 0.657                           2.57
    LiPo               0.90–2.63     0.36 –0.95         
                      Mean: 1.77     Mean: 0.66                             2.7

    * Lower Heating Value (LHV)

Jet A1 fuel is practical, besides the unfortunate fact that it is extremely inexpensive per liter, because it has both a good energy density (34.7 MJ/L) and specific energy (43.2 MJ/L). LH2 has a much higher specific energy (119.8 MJ/kg) but a much lower energy density (8.491 MJ/L). Both Li-ion and LiPo have poor energy densities and specific energies; note that their mean values have been taken to be conservative, although using one value or another for the Li-ion and LiPo energy storage media matters little as their energy densities and specific energy do not compare to jet A1 and LH2.

The A320ceo can carry up to 27,200 L, or 21,900 kg, of jet A1 fuel. For the purposes of studies, it is assumed that the fuel capacity of the A320ceo will not be modified (though the energy storage media, with which it is filled, will be). The AT200 can carry up to 5,000 L or 1,500 kg of cargo---depending on whether the volume or the mass of the cargo is the limiting factor. It is also assumed for the purposes of the studies that no significant additional volume or weight will need to be carried by either the airliner or the UAV to support different fuels (which does not necessarily hold true for fuels such as LH2).

The following table compares the volume, mass, and energy of fuels that the A320ceo airliner and AT200 UAV are capable of carrying based solely on their fuel/cargo capacity volumes---not yet considering their fuel/cargo capacity masses). Note that, for the AT200 UAV, fuel is referring to that with which it will refuel the airliner, which is treated as cargo. Asterisks indicate where the fuel/cargo capacity volume is correctly the limiting factor, which is always the case for the A320ceo (or, correspondingly, the fuel density always being too low), and for the AT200 with the exception of LH2 due to its exceptionally low density. The Li-ion and LiPo fuels are less dense than jet A1, and LH2 far less dense. Whereas the A320ceo has enough space for 21,900 kg of jet A1, only 1,930 kg of LH2 can occupy the same space; whereas the AT200 has enough space for 4,000 kg of jet A1 (ignoring the 1,500-kg cargo capacity volume of the AT200), only 350 kg of LH2 can occupy the same space. The fuel/cargo volume capacity is reached before the fuel/cargo mass capacity.

::

    Aircraft   Fuel      Fuel Volume (L)    Fuel Mass (kg)    Fuel Energy (MJ)
    ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    A320ceo    Jet A1          *  27,200         *  21,900             944,000
               LH2             *  27,200             1,930             231,000
               Li-ion          *  27,200            17,900              46,100
               LiPo            *  27,200            17,800              48,000
    ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    AT200      Jet A1              5,000             4,000             170,000
               LH2             *   5,000               350              40,000
               Li-ion              5,000             3,000               8,500
               LiPo                5,000             3,000               8,800

    Calculated values are rounded and significant
    figures are respected where reasonable.

The following table uses the fuel/cargo capacity masses. Asterisks indicate where the fuel/cargo capacity mass is correctly the limiting factor, which is always the case for the AT200 (with the exception of LH2), indicating that the mass-to-volume ratio of the AT200 is poorly optimized for carrying many fuels.

::

    Aircraft   Fuel      Fuel Volume (L)    Fuel Mass (kg)    Fuel Energy (MJ)
    ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    A320ceo    Jet A1          *  27,200         *  21,900             944,000
               LH2               309,000            21,900           2,620,000
               Li-ion             33,300            21,900              56,400
               LiPo               33,400            21,900              58,900
    ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    AT200      Jet A1              2,000         *   1,500              65,000
               LH2                20,000             1,500             180,000
               Li-ion              2,000         *   1,500               3,900
               LiPo                2,000         *   1,500               4,000

    Calculated values are rounded and significant
    figures are respected where reasonable.

The following table uses both the fuel/cargo capacity volumes and masses to obtain the correct values; it is a merging of the previous two tables. Asterisks indicate where the fuel/cargo capacity volume or mass is the correct limiting factor. The limited fuel/cargo capacity volume of the A320ceo and AT200 prevent them from being able to carry up to 2,620 and 0.18 GJ of energy, respectively, as that would require 309,000 and 20,000 L of space---11× and 4× what the A320ceo and AT200 provide.

::

    Aircraft   Fuel      Fuel Volume (L)    Fuel Mass (kg)    Fuel Energy (MJ)
    ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    A320ceo    Jet A1          *  27,200         *  21,900             944,000
               LH2             *  27,200             1,930             231,000
               Li-ion          *  27,200            17,900              46,100
               LiPo            *  27,200            17,800              48,000
    ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
    AT200      Jet A1              2,000         *   1,500              65,000
               LH2             *   5,000               350              40,000
               Li-ion              2,000         *   1,500               3,900
               LiPo                2,000         *   1,500               4,000
    
    Calculated values are rounded and significant
    figures are respected where reasonable.

    1 MJ is 0.28 kWh.

The A320ceo can store 4 times as much energy in the form of jet A1 (944 GJ or 262 MWh) as it can store as LH2 (231 GJ or 64.2 MWh). Even at capacity, this is not enough LH2 to maintain operations. Notably, at 46.1 GJ or 48.0 GJ, Li-ion or LiPo energy storage media are out of the question.

The AT200 can store 40 GJ of LH2---62% as much as it can store jet A1 (in terms of energy) due to its large cargo volume-to-mass ratio.

Whereas a jet-A1-fueled A320ceo need not take off with its maximum capacity of fuel unless flying its maximum range, a LH2-fueled A320ceo would take off with maximum capacity to minimize the number of times it must be refueled by UAV. Notably, carrying this extra capacity of a fuel that is no less dense than jet A1 would result in decreased efficiency, whereas carrying LH2 results in increased efficiency due to its low density.

An LH2-fueled A320ceo would need to be refueled by X UAVs to have the same range as a jet-A1-fueled A320ceo. However, the deviations from the regular flight path to be refueled over airports en route would increase the distance traveled, thereby reducing the effective range.

Assuming that the A320ceo starts with maximum fuel, the following graph illustrates its energy level over time from JFK to LAX, parameterized by different energy storage media and whether or not the A320ceo is refueled the minimum required amount to stay above a 100-GJ reserve level where possible. If refueled, the A320ceo is refueled over PIT and DEN as many times as necessary for it to stay above the reserve level by the time it reaches its next airport.
