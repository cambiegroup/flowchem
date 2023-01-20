from fastapi import FastAPI

app_db = FastAPI()

@app_db.get("/")
def read_root():
    return {"Hello":"World"}


@app_db.get("/db/experiment{id}")
async def get_experiment_by_id():
    return None


@app_db.put("/db/experiment{id}")
async def set_experiment_by_id(id, data):
    return None






if __name__ == "__main__":
    pass
    # app_db.run(port=8080)
    #run at Terminal: unicorn db_control:app_db --reload --port 8080


