# Conservative transport computation

This is a real executed **synthetic numerical computation**, not field measurements or empirical evidence. Five irregular-volume cells exchange an amount through six symmetric internal conductances. The authored CC0 producer uses edge fluxes and exact fractions; PCS's separate receiver uses a transition matrix.

Run `python run_workflow.py` here to create the exact concentration trajectory. The typed contract declares the modeled topology, units, explicit time step, initial concentrations, data origin and physical applicability assumptions. It does not establish continuum discretization error, geometry-derived conductances, material behavior or thermodynamic energy. The decreasing diagnostic is a volume-weighted squared-concentration functional, with units mol²/m³.

From a PCS core checkout run `python scripts/run_scientific_workflow_v3.py --output /tmp/pcs-transport-new`. This builds existing signed PCS packages and independently replays them, including conservation-preserving but incorrect trajectories and legitimate producer-signature forgeries.

All files in this example are newly authored and dedicated to CC0 1.0 Universal. No external empirical dataset, private data or human participation is used.
