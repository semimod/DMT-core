@startuml
actor User as user
participant SimCon as sim_con
collections DutViews as dut_views
user -> sim_con : run_and_read(duts, sweeps)
sim_con -> dut_views : generate_inputs(sweeps)
@enduml
