# Architecture

Modular package under `pcs_next_v1/` with fail-closed boundaries:

Producer → Intake/Freeze → Pilot SM → Evidence Store → (optional) Authority probe  
Receiver → Pin Policy → Independent Review → Assurance Card

Core verification logic is CLI-accessible without the workbench UI.
