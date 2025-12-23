import logging

logging.getLogger().handlers.clear()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

if __name__ == "__main__":
    logging.info(
        "CSV/CLI launchers have been removed. Use the FastAPI server to submit runs."
    )
