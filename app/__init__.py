import logging

logging.root.handlers = []
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO,
                    filename='triggear.log')

console = logging.StreamHandler()
console.setLevel(logging.WARNING)
logging.getLogger("").addHandler(console)
