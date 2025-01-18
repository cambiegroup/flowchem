from loguru import logger
from textwrap import dedent

def fakeassemble_finder(*args) -> set[str]:
    logger.debug(f"The fake device is always easy to find!")
    cfg: set[str] = set()
    cfg.add(
        dedent(
            f"""[device.my_fakeassemble]  # type:ignore
                    type = "FakeAssemble"\n\n""",
        ),
    )
    return cfg