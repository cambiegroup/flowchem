from gryffin import Gryffin

logger.add("./xp.log", level="INFO")

# load config
config_0 = {
    "parameters": [
        {"name": "SOCl2_equivalent", "type": "continuous", "low": 1.0, "high": 1.5},
        {"name": "temperature", "type": "continuous", "low": 30, "high": 65},
        {"name": "residence_time", "type": "continuous", "low": 2, "high": 20},
    ],
    "objectives": [
        {"name": "product_ratio_IR", "goal": "max"},
    ],
}

config = {
    "parameters": [
        {"name": "EosinY_equivelent", "type": "continuous", "low": 0.0, "high": 0.1},
        {"name": "activator_equivelent", "type": "continuous", "low": 0.0, "high": 0.1},
        {"name": "quencher_equivelent", "type": "continuous", "low": 0.0, "high": 0.1},
        {"name": "solvent_equivelent", "type": "continuous", "low": 0.0, "high": 0.1},
        {"name": "oxygen_equivelent", "type": "continuous", "low": 0.0, "high": 0.1},
        {"name": "pressure", "type": "continuous", "low": 0.0, "high": 6.0},
        {"name": "SM_concentration", "type":"continuous", "low": 0.025, "high": 1.22},
        {"name": "temperature", "type":"continuous", "low": 0, "high":70},
        {"name": "residence_time", "type":"continuous", "low": 0.5, "high":70}
    ]
}

# Initialize gryffin
gryffin = Gryffin(config_dict=config)
observations = []
