import logging

class Logger:
    def __init__(self, name="bot"):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(message)s"
        )
        self.logger = logging.getLogger(name)

    def info(self, msg):
        self.logger.info(msg)

    def error(self, msg):
        self.logger.error(msg)

# logger = Logger()  # agar object yaratmoqchi bo‘lsangiz
