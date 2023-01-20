import asyncio
from typing import Optional
import pymongo
from pydantic import BaseModel
from loguru import logger

# MongoDV driver
from motor.motor_asyncio import AsyncIOMotorClient

from beanie import Document, Indexed, init_beanie

config = {
    "parameters": [
        {"name": "EosinY-equivelent", "type": "continuous", "low": 0.0, "high": 0.1},
        {"name": "activator-equivelent", "type": "continuous", "low": 0.0, "high": 0.1},
        {"name": "quencher-equivelent", "type": "continuous", "low": 0.0, "high": 0.1},
        {"name": "solvent-equivelent", "type": "continuous", "low": 0.0, "high": 0.1},
        {"name": "oxygen-equivelent", "type": "continuous", "low": 0.0, "high": 0.1},
        {"name": "pressure", "type": "continuous", "low": 0.0, "high": 6.0},
        {"name": "SM_concentration", "type": "continuous", "low": 0.025, "high": 1.22},
        {"name": "temperature", "type": "continuous", "low": 0, "high": 70},
        {"name": "residence-time", "type": "continuous", "low": 0.5, "high": 70},
        {"name": "light-intensity", "type": "continuous", "low": 50, "high": 100}
    ]
}


class Category(BaseModel):
    name: str
    description: str


class Experiment(Document):
    name: str
    description: Optional[str] = None
    SM_concentration: float
    time: float
    eosinY_equiv: float
    activator_equiv: float
    quencher_equiv: float
    oxygen_equiv: float
    solvent_equiv: float
    pressure: float
    temperature: float
    UV: int
    category: Category

    class Settings:
        name = "BV_1"  # MongoDB collection name


async def insert_new_exp():

    BV_description = Category(name="BV_inflow", description="Preforming Baeyer–Villiger oxidation with EosinY in flow")

    # TODO: the experiment number should be same with the electronic notebook on https://eln02.mpikg.mpg.de/main
    num = 136
    # TODO: function to insert new experiment to the database
    # Beanie documents work just like pydantic models
    whh_136 = Experiment(name=f"WHH-{num}",
                         SM_concentration=1.22,
                         time=25.0,
                         eosinY_equiv=0.01,
                         activator_equiv=0.02,
                         quencher_equiv=2.0,
                         oxygen_equiv=2.0,
                         solvent_equiv=10.0,
                         pressure=4.0,
                         temperature=30.0,
                         UV=100,
                         category=BV_description
                         )
    # insert the next experiment wanted to do into the database
    print(await whh_136.insert())  # return the _id

    # insert many documents
    # await Experiment.insert_many([whh_136,whh_137])


async def find_document():
    # You can find documents with pythonic syntax
    exp_time_gt_10 = await Experiment.find_one(Experiment.time > 10)
    print(exp_time_gt_10)


    # # And update them
    # await exp_time_lt_10.set({Experiment.time: 10})

def find_lastest_suggestion() -> dict:
    # Sort the documents by the "created_at" field in descending order
    latest_doc = Experiment.find_one(sort=[("created_at", -1)])  # chatGPT
    latest_doc["id"] = str(latest_doc["_id"])
    return latest_doc

async def main_db():
    """ This is an asynchronous example, so we will access it from an async function"""
    # Beanie uses Motor async client under the hood
    client = AsyncIOMotorClient("mongodb: // localhost: 27017")
    # client = AsyncIOMotorClient("mongodb+srv://cynthiabour:mpikgchemistry2022@cluster0.glr1fvv.mongodb.net/test")
    # database: client.BV_experiments
    # collection = database.experiment

    # Initialize beanie with the Experiment document class
    # database: the database saved the data
    await init_beanie(database=client.BV, document_models=[Experiment])




if __name__ == "__main__":
    asyncio.run(main_db())
