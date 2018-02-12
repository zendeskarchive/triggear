import logging

logging.root.handlers = []
fmt = '%(asctime)s %(levelname)-8s %(message)s'
logging.basicConfig(format=fmt,
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO,
                    filename='triggear.log')

console = logging.StreamHandler()
console.setLevel(logging.WARNING)
console.setFormatter(logging.Formatter(fmt))
logging.getLogger("").addHandler(console)
