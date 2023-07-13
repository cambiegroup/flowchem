from pydantic import BaseModel

__all__ = ["Person", "dario", "jakob", "wei_hsin"]


class Person(BaseModel):
    name: str
    email: str


dario = Person(name="Dario Cambiè", email="2422614+dcambie@users.noreply.github.com")
jakob = Person(name="Jakob Wolf", email="Jakob.Wolf@mpikg.mpg.de")
wei_hsin = Person(name="Wei-Hsin Hsu", email="Wei-hsin.Hsu@mpikg.mpg.de")
