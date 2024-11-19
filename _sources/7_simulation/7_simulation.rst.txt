Simulation
==========

A simulation was developed to aid in the modeling and understanding of the SoC, speed, location, and other properties of the airliner and UAVs over time, for the duration of an entire flight. It includes the takeoff, climb, descent, and landing of each of the aircraft as well as the interaction between the airliner and each UAV throughout the flight.

Visual simulation
-----------------

A visual extension of the simulation allows the aircraft to be visualized in a virtual environment while the simulation runs, along with the SoC and speed of the airliner.

The following video and walkthrough build upon the previous feasibility study and follow the flight path of a hydrogen-powered A320 from JFK to LAX.

Video
^^^^^

.. raw:: html

    <style>
    .responsive-video-container {
        position: relative;
        padding-bottom: 56.25%; /* 16:9 */
        padding-top: 25px;
        height: 0;
    }
    .responsive-video-container embed {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
    }
    </style>
    <div class="responsive-video-container">
        <embed src="https://www.youtube.com/embed/5WDB9vRs0N4" allowfullscreen></embed>
    </div>

https://www.youtube.com/embed/5WDB9vRs0N4

Walkthrough
^^^^^^^^^^^

.. raw:: html

    <style>
    img {
        border: 1px solid #777777;
    }
    </style>

Like the video, the following walkthrough shows the airliner, its SoC and speed graphs, the UAVs, and a map view at various stages in the airliner's flight.

The airliner takes off from JFK international airport. At the same time, two AT200 cargo UAVs are waiting at Pittsburgh International Airport (PIT).

.. image:: 1.png

`1:02 in video <https://youtu.be/5WDB9vRs0N4&t=62>`_

The first UAV takes off from PIT. The second PIT UAV is still waiting.

**Refueling at Pittsburgh International Airport.** TODO minutes into the flight, TODO km from PIT, the airliner begins to slow down to match the speed of the first, incoming UAV (as shown in the Airliner Speed graph):

.. image:: 2.png

`1:17 in video <https://youtu.be/5WDB9vRs0N4&t=77>`_

The UAV circles back and descends to the altitude of the airliner. The UAV starts to refuel the airliner in mid-air, from TODO to TODO SoC:

.. image:: 3.png

`1:26 in video <https://youtu.be/5WDB9vRs0N4&t=86>`_

After refueling, the UAV ascends from the airliner, which remains at reduced speed in preparation for a second refueling. The UAV temporarily slows down to fall behind the airliner, before descending below the cruise altitude of the airliner. The UAV subsequently lands at PIT, while a second UAV is taking off:

.. image:: 4-1.png

`1:42 in video <https://youtu.be/5WDB9vRs0N4&t=102>`_

The second UAV refuels the airliner to TODO SoC and circles back to land at PIT. The airliner returns to cruise speed and is now en route to Denver International Airport (DEN).

.. image:: 7.png

`2:03 in video <https://youtu.be/5WDB9vRs0N4&t=123>`_

**Refueling at Denver International Airport.** TODO minutes into flight, the SoC of the airliner is at a mere TODO. The refueling process starts at DEN. TODO km from DEN, the airliner begins to slow down to match the speed of the first, incoming UAV from DEN:

.. image:: 8.png

`2:14 in vdeo <https://youtu.be/5WDB9vRs0N4&t=134>`_

After the first, two further UAVs refuel the airliner, bringing it to TODO SoC. After refueling the airliner, each UAV descends to a different altitude to give each other enough clearance before landing in succession at DEN. At the same time, two additional UAVs are taking off from DEN for the further refueling required to reach LAX with some reserve.

.. image:: 11-1.png

`2:44 in video <https://youtu.be/5WDB9vRs0N4&t=164>`_

After the additional two UAVs ascend from refueling the airliner and start to circle back to DEN, the airliner returns again to cruise speed, en route to LAX.

.. image:: 15.png

`2:54 in video <https://youtu.be/5WDB9vRs0N4&t=174>`_

TODO minutes into flight, the airliner begins its descent to LAX:

.. image:: 16.png

`3:05 in video <https://youtu.be/5WDB9vRs0N4&t=185>`_

After TODO minutes, the airliner lands at LAX with a reserve of TODO SoC:

.. image:: 17.png

`3:15 in video <https://youtu.be/5WDB9vRs0N4&t=195>`_
