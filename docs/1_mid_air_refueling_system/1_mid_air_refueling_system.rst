.. _mid_air_refueling_system:

Mid-Air Refueling System for Commercial Aviation
================================================

Background
----------

Mid-air refueling, also known as aerial refueling, uses a tanker aircraft to refuel a receiving aircraft during flight. This allows the receiving aircraft to stay airborne for longer, without having to land to refuel, thereby extending its effective range. There are two existing systems for mid-air refueling: probe-and-drogue and flying boom.

Probe-and-drogue is easier to retrofit to existing aircraft. TODO

Flying boom TODO

Mid-air refueling allows the receiving aircraft to cover the same distance with less fuel onboard. The fuel that does not have to be carried by the receiving aircraft is instead carried by the tanker aircraft. If the tanker does not have to travel as far as the receiving aircraft, mid-air refueling actually results in overall fuel savings, as the receiving aircraft does not have to burn extra fuel just to carry extra fuel. This accounts for the fuel consumed by the tanker. More fuel is saved if the tanker is more fuel efficient than the receiving aircraft, which is true if the receiving aircraft is a jet fighter in the context of a military operation, but can still be true if the receiving aircraft is a commercial airliner if a larger tanker is used.

Because of these fuel savings, even if still using conventional jet fuel, mid-air refueling is a way to reduce the CO₂ emissions (and costs) of flights covering distances of 5--6,000 km or more. Long-haul flights are estimated to need only 60--65% as much fuel, potentially. A fear, however, is that this will result in reduced air fares and increased demand for flights which, if satisfied, would offset the CO₂ reductions from fuel savings.

----

.. TODO diagrams

The airliner would be refueled by one or more UAVs over the course of its flight from origin airport to destination airport.

To facilitate the operations required to store, maintain, refuel, recharge, launch, and monitor these UAVs, the UAVs would most practically operate out of international airports between the origin and destination. The UAVs would share the same kind of provisions and services used by airliners operating out of these flyover airports (hangars, refueling equipment, runways, and air traffic control), but would most practically be owned by the airport and shared between airlines rather than owned by separate airlines. Such flyover airports and their services would be expanded as necessary to operate the UAVs. Airliners would be charged for their use of UAV operations.

Whether to alter the airliner's flight path to meet the UAV(s) over their flyover airports (option A) or to alter each UAV's flight path to meet the airliner (option B) would require an analysis factoring in the locations of the airports involved and the burn rate of the fuel (or whichever energy storage medium) per distance traveled of the UAV(s) versus that of the airliner. Moreover, determining an optimal compromise between options A and B would require solving an optimization problem for each airliner flight path given its UAV(s).

However, the most important factor is safety, in whose consideration option A---in which airliners fly in the airspace of flyover airport(s) to be refueled by UAV(s)---is most viable. Although the UAV(s) are uncrewed, if there is a problem surrounding the recharging process, the airliner can safely land at the flyover airport. Thus, Option A is assumed both for this study and for the 3D computer simulation.

The desire for the aforementioned backup plan in case of an emergency has implications on precisely when, where, and how in the flyover airport's airspace the airliner would be refueled. For maximum safety, the airliner would likely be refueled in the flyover airport's airspace while flying towards rather than from the airport to avoid having to circle back to it before landing in case of an emergency during recharging. However, this likelihood and the exact flight path taken by the airliner through the airport's airspace would depend on the configuration of the airport's runways and would be computed for each airliner flight path given its UAV(s). For this study, in line with its inherent simplifications, it is assumed that the airliner is refueled to its new SoC instantly upon flying directly over the flyover airport. For the 3D computer simulation, it is assumed that the airliner flies directly over the flyover airport, with the exception of any curve in its flight path as it does so, and the airliner is refueled as it flies towards the airport and possibly as it flies away from it as well.

Each UAV would be fueled, and its battery charged, by its airport services. Each UAV would autonomously follow each stage of the following flight plan and UAV sequence:

1. Taxi, takeoff, and climb.
2. Navigate to and intercept with the airliner's flight path.
3. Dock with the airliner, charge the airliner, and undock.
4. Clear the airliner and navigate back to its originating airport.
5. Descend, land, and taxi.

Airliner--UAV Interaction and Surrounding Design
------------------------------------------------

It may be desirable for the UAV to fly very close to the airliner and that a relative position between the two aircraft be maintained (station-keeping). To make this easier and improve safety, it may furthermore be desirable for the UAV to be attached to and/or land on a surface of the airliner's fuselage. This would especially be the case if there are reasons why a traditional mid-air refueling system in which the two aircraft fly separately is impractical, or if the UAV's transfer of energy to the airliner takes the form of exchanging a spent battery for a charged one. Landing the UAV on the airliner's surface, the first step of the proposed docking sequence between the two, may be accommodated and made possible given the large size of the airliner relative to the small size of the UAV.

The UAV landing on the airliner is not analogous to landing on a runway. When landing, both the aircraft-to-runway relative velocity and the aircraft-to-air relative velocity (whose magnitude is the aircraft's airspeed) are relevant. On a runway, these two relative velocities are often the same or similar because both the runway and the air are stationary (or at least the air is often near-stationary with calm winds). On a runway, the landing aircraft must essentially match the runway's velocity (zero), but after making contact with the runway; the aircraft slows both before and after touchdown and thus the runway must be of a certain minimum length. Whereas for the UAV landing on the airliner's surface, the UAV must make its own aircraft-to-runway relative velocity (where the *runway* is actually the commercial airliner) equal to zero by matching its airspeed with that of the commercial airliner. This can be done entirely before the UAV has touched down because it will still have enough airspeed (equal to that of the commercial airliner) to sustain lift. Thus, the UAV does not need a long runway which the airliner is unable to provide. The UAV does not need to be stationary relative to the airliner upon landing; it may need to adjust its position forwards *or backwards* and can do so using its own propulsion because its airspeed will be much higher than if it were landing on a runway. Note that all of the above assumes the UAV to land on the airliner's surface in the same direction of travel as the airliner; lift considerations aside, landing in the opposite direction would require the UAV to be able to propel itself in reverse.

In the intended operation, mid-flight and along its route, as the airliner approaches the airspace of an airport below, a UAV would take off from that airport, climb toward the airliner's altitude, and approach the airliner in preparation to begin the docking sequence by landing on its top surface. Although it would be more efficient and safer for the UAV to approach the airliner with the two aircraft pointing towards each other, and for the UAV to thus land on the airliner in antiparallel, this arrangement is impossible for a UAV that, like the AT200 cargo UAV, cannot propel itself in reverse. However, it is worth discussing the arrangement's benefits. The arrangement would be more efficient because the airliner would likely still be facing in the direction of the airport (from which the UAV took off) when the UAV is approaching. The arrangement would arguably be safer because, although under normal operation the UAV would be autonomous and the airliner's pilot would not need to intervene, the arrangement allows the airliner pilot to see the UAV's approach. Notably, having at least the landing of the UAV on the airliner and the subsequent start of refueling occur when the airliner has not yet passed the airport is also safer because it allows for the airliner to more easily make an emergency ground landing in the abnormal cases of it being damaged in the UAV'S landing or, due to some other failure, not being left with enough energy to continue its normal route.

If the UAV is to land on top of the airliner's fuselage, the UAV's landing gear, as on a runway, would to some extent cushion its impact with the airliner's fuselage, and allow the UAV to roll to a complete stop relative to the airliner's speed. A disadvantage of the UAV landing on top is that it must fly above or around the airliner's tail stabilizers to evade them. An alternative, the UAV docking beneath the airliner, may require a different approach for making the UAV--airliner attachment. The following assumes the UAV to land on the top of the airliner.

**A summary of the docking and coupling sequence between the airliner and UAV is as follows:**

- The UAV lands on the top surface of the airliner. The UAV is guided into position by its wheels entering grooves in the top surface of the airliner's fuselage.
- The UAV's alignment with the airliner is maintained by wedge-shaped blocks which extend into said grooves.
- A coupling arm rotates out of a compartment in the airliner's top surface and hooks onto an anchor point in a compartment within the underbelly of the UAV, to hold it in place.
- Similarly, an energy transfer arm rotates out of the airliner's top surface and connects to a matching plug or port in the UAV's underbelly.

After this sequence, the transfer of energy begins. After the energy transfer concludes, the sequence is followed in reverse: the arms disconnect and retract in reverse order, the wedge-shaped blocks retract, and the UAV can proceed to a kind of take-off which is aided by the fact that the UAV will already have significant airspeed.

**The steps of the docking and coupling sequence, and the engineering design to enable them, are described in the following sections.**

The following designs require space within the fuselage above the passenger cabin. Most narrow-body airliners, the A320 included, do not have a lot of space, let alone empty space, between the ceiling of the passenger cabin and the top surface of the fuselage. What distance there is in between is occupied by the reinforced structure of the fuselage, after which aisle headroom for passengers is a priority. However, both aisle headroom for passengers and seating headroom and/or the height of overhead luggage bins can be sacrificed to some degree.

Design of Modifications to the Commercial Airliner
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Guiding the UAV into Position**

The UAV should ideally be guided into the correct position along the length of the airliner's fuselage to compensate for any slight inaccuracies in the UAV's control, or turbulence. To achieve this, the top surface of the airliner's fuselage would be modified to have three grooves along its long axis, one groove for each of the UAV's three landing gear wheels, with the spacing between the three grooves equal to that between the three wheels. The UAV would land in these grooves, which would keep the UAV aligned with the airliner while the UAV is parked. The grooves would also help align the UAV while it lands; each groove would start wide and shallow before becoming almost as deep as each wheel's radius and almost as narrow as each wheel's width. Thus, if the UAV is somewhat misaligned with the airliner in the left-to-right or back-to-front directions while landing, the grooves will guide the UAV into the correct position. The side walls and especially the bottom of the grooves would be reinforced to sustain the impact and weight of the UAV.

**Maintaining Alignment with the UAV**

Once the UAV has been guided into position, its alignment with the airliner must be maintained. Wedge-shaped blocks, usually retracted and flush with the bottom of the grooves, would rotate up to keep the UAV, by its wheels, in place. The blocks can be made of machined aluminum. There would be two blocks per groove, one for the front and back of each wheel, to stop each from rolling forwards or backwards. Because the blocks rotate to extend out or retract, they stay flush with the grooves and thus with the surface of the airliner's fuselage except where they meet the UAV's wheels. The blocks would be retracted when it is time for the UAV to depart.

Design of Modifications to both the Commercial Airliner and UAV
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Attaching the UAV to Hold it in Place**

Once the UAV is secured in the correct alignment with the airliner, it must be attached to the airliner to hold it in place. This process will be termed *coupling*, and the reverse process of releasing the UAV from the airliner is termed *uncoupling*. The landing gear of the AT200 cargo UAV is not suitable to hold the UAV down once landed, nor is it designed to. Instead, modifications to both the UAV and airliner would serve to make the attachment between the two; in particular, a coupling arm.

To hold the UAV down against the airliner, this machined aluminum arm would rotate out of the airliner's top surface to become perpendicular to the fuselage and latch onto a designed anchor point on the underside of the UAV. In this first degree of freedom, the arm can be rotated by a stepper motor or hydraulic motor within the airliner's fuselage. The arm would be of airfoil-like cross section to reduce air resistance. To keep the airliner's top surface streamlined when the arm is rotated fully outwards or inwards, narrow flaps would enclose and cover the compartment that houses the arm when retracted. This also keeps the compartment free of debris. The flaps can be hinged and spring-loaded, or otherwise flexible, such that they return to their closed position by default, and open outwards or inwards when the arm rotates out of its compartment or back into it, respectively.

The UAV's anchor point would be hooked onto by the end of the arm through a compartment in the underside of the UAV, similar to the airliner's compartment but smaller. The underside of the UAV is kept streamlined and the compartment free of debris by a hinged and spring-loaded, or otherwise flexible, flap which usually covers the compartment. While the end of the arm is rotated into the compartment, it deflects this flap inwards and out of the way.

The anchor point of the UAV is a steel bar in its underbelly and the end of the arm is shaped to act like a hook to attach to it. In one configuration of the arm, the end of the arm is spring-loaded as its second degree of freedom and the end of the hook shape is tapered from both sides to hook onto and off of the steel bar by the torque of the stepper motor. In another more likely configuration, the arm is hydraulic such that it may effectively increase and decrease in length in its second degree of freedom, pulling the hook shape over the steel bar and lifting it off of the bar for coupling and uncoupling, respectively.

**Connecting to the UAV for Energy Transfer**

Once the coupling between the airliner and UAV is complete, a connection must be made to enable energy transfer therebetween. The coupling could also be used for the energy connection, but the two subsystems will be kept separate for safety/redundancy and simplicity. For example, the second degree of freedom of the coupling arm would make additionally using the arm for the energy connection difficult. A separate energy transfer arm is designed. For energy storage media, this arm, unlike the coupling arm, would likely have to extend in length to make the connection and retract its length to sever it. This applies to an electrical charging connector as well as a connector for liquid or gaseous fuel.

The external design of the arm is similar regardless of the energy medium used. For example, if the medium is electricity, then a connector like that of the Megawatt Charging System (MCS), which is in development for charging very large electric vehicles at up to 3.75 MW, may be used. The MCS connector is of approximately the same size as the connector of a refueling hose for an airliner.

The design of the energy transfer arm and its integration in the airliner's fuselage is similar to that of the coupling arm. The energy transfer arm would also rotate out of the airliner's top surface. The end of the arm would hydraulically extend or retract to make or sever its connection, respectively, with its stationary counterpart on the bottom of the UAV.
