Design and Feasibility Study of Mid-Air Refueling of a Hydrogen-Powered Airliner
================================================================================

.. image:: collage.png

Decarbonizing Aviation: Lost Cause or an Inevitable Outcome?
------------------------------------------------------------

Aviation releases massive amounts of greenhouse gas (GHG) emissions and contributes to approximately 2.5% of global CO₂ emissions. It makes the most sense to attempt to create solutions to the largest portions of CO₂ and other GHG emissions first, and solutions are thusly being developed (albeit not quickly enough) to decarbonize the world's electrical grids, manufacturing, and transportation, the latter including electric cars and similar electric vehicles. However, despite many of these sectors being challenging to electrify or reduce their emissions by other means, doing so for travel by air remains elusive due to its inherent inefficiency and need of enormous amounts of energy. Aviation is one of the most challenging sources of global CO₂ emissions due to difficulty in decarbonizing it. To reach net zero CO₂ emissions by 2050, the 2.5% global contribution of air travel must eliminated and the industry decarbonized. Furthermore, the depletion of oil reserves toward the end of the century will require that this be done soon, or alternatives be found, regardless.

**Not Just CO₂.** It should be noted that while aviation contributes to 2.5% of global CO₂ emissions, it contributes in total to 3.5% of the world's *effective radiative forcing*, which is a more complete metric for aviation's affect on the warming of the earth. In other words, aviation causes a disproportionately large share of warming relative to its share of CO₂ emissions. This is because only one third of the effective radiative forcing is caused by CO₂, most of the remainder being caused by contrails of water vapor which is a stronger GHG despite its significantly shorter half-life in the atmosphere. This is not an excuse to continue jet-fueled air travel and will also be accounted for when considering alternative fuels.

.. https://ourworldindata.org/co2-emissions-from-aviation
..     https://ars.els-cdn.com/content/image/1-s2.0-S1352231020305689-gr3_lrg.jpg
..     "Although CO2 gets most of the attention, it accounts for less than half of this [3.5%] warming. Two-thirds (66%) comes from non-CO2 forcings. Contrails – water vapor trails from aircraft exhausts – account for the largest share."
..         Reduce water vapor output of propulsion? Motors would; biofuels and H2 would not.

Using alternative fuels, however, poses a challenge. The specific energies of all practical alternative fuels (except drop-in replacement fuels) pale in comparison to that of jet fuel. Specific energy is energy per unit weight---obviously a critical metric for aviation.

What's this Project?
--------------------

This project proposes a :ref:`mid-air refueling system for commercial aviation <mid_air_refueling_system>` in attempt to work with alternative fuels' poor specific energies. A :ref:`feasibility study <feasibility_studies>` is presented for alternative fuels along a frequent domestic flight path. Finally, a :ref:`simulation <simulation>` is developed to show how one of the alternative fuels can be used along said flight path, with---and only with---the mid-air refueling system.

The mid-air refueling system uses UAVs to refuel the airliner during each flight. The system seeks to avoid reinventing the wheel in terms of the technologies required. Rather than trying to redesign decades-old aircraft from scratch, the system requires only retrofitting existing airliners and prototype UAVs that are based on existing airplanes. If a product or piece of equipment is not already available, it should be reasonable to fabricate. This project aims not to propose a far-fetched yet well-marketed concept, but to discusses potential ideas using mostly existing if not already widespread technology.

A notable limitation of this study is that it does not include or discuss the modified power plant (engine or motor) of the airliner.

.. toctree::
   :maxdepth: 1

   1_mid_air_refueling_system/1_mid_air_refueling_system.rst
   2_airliner_uav_selection/2_airliner_uav_selection.rst
   3_feasibility_studies/3_feasibility_studies.rst
   4_simulation/4_simulation.rst
   5_simulation_configuration/5_simulation_configuration.rst
   6_optimizing_flyover_airports/6_optimizing_flyover_airports.rst
