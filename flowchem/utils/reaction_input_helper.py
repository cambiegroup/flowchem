from ord_schema.proto.reaction_pb2 import ReactionInput, Compound, CrudeComponent, ReactionRole, ReactionIdentifier, CompoundPreparation, FlowRate
from flowchem.units import flowchem_ureg


def add_flowrate_to_input(reaction: ReactionInput, flowrate_text: str):
    """ Add a flowrate to a reaction. """

    # Parse the flowrate
    flowrate = flowchem_ureg(flowrate_text)
    assert flowrate.units == flowchem_ureg.volume / flowchem_ureg.time, "Flowrate must be in units of volume/time"

    # Convert it to ml/min (we could use different ORD values, but this is easier)
    flowrate.ito(flowchem_ureg.milliliter / flowchem_ureg.minute)

    # Make it into a protobuf
    flow_rate_pb = FlowRate()
    flow_rate_pb.value = flowrate.magnitude
    flow_rate_pb.units = FlowRate.FlowRateUnit.Value("MILLILITER_PER_MINUTE")

    # Add the flowrate to the reaction
    reaction.flow_rate.CopyFrom(flow_rate_pb)

    return reaction
