from abc import ABC
from abc import abstractmethod

import uvicorn
from fastapi import APIRouter
from fastapi import FastAPI


def set_r4(ch, temp):
    print(f"set ch {ch} to {temp}")


app = FastAPI()


class HW_Dev:
    def set_temp(self, channel, temp):
        print(f"setting temp {temp} to chanel {channel}")

    def components(self):
        return [MyHWTemp(tc, self) for tc in range(10)]


class TC(ABC):
    def __init__(self, name: str):
        print(f"INIT TC WITH  {name}")
        self.name = name
        self.router = APIRouter(prefix=f"/{self.name}")
        self.router.add_api_route("/set-temp", self.set_temp, methods=["GET"])
        self.router.add_api_route("/metadata", self.set_temp, methods=["GET"])

    @abstractmethod
    def set_temp(self, temperature):
        pass


class MyHWTemp(TC):
    def __init__(self, number, parent_hw_dev):
        name = f"DEV_{number}"
        super().__init__(name)
        self.hw = parent_hw_dev
        self.number = number

    def set_temp(self, temperature):
        self.hw.set_temp(temp=temperature, channel=self.number)


hw = HW_Dev()

for component in hw.components():
    app.include_router(component.router)

uvicorn.run(app)
