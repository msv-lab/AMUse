import logging

logging.addLevelName(logging.DEBUG, "VERBOSE")
Logger = logging.getLogger("AMUSE")

Logger.setLevel(logging.INFO)

consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.DEBUG)
consoleHandler.setFormatter(
    logging.Formatter(
        "%(levelname)s ----- %(message)s ----- %(asctime)s",
        datefmt="%d/%m/%Y %I:%M:%S %p",
    )
)


Logger.addHandler(consoleHandler)
