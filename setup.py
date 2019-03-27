import sys
from distutils.core import setup

if sys.version_info.major < 3:
    raise Exception("jab only works with Python 3.7+")

if sys.version_info.major == 3 and sys.version_info.minor < 7:
    raise Exception("jab only works with Python 3.7+")


VERSION = "0.1.0"

DEPENDENCIES = ["typing_extensions", "starlette", "jab"]
DEP_LINKS = ["git+https://github.com/stntngo/jab@master#egg=jab-v0.3.0"]

setup(
    name="eggman",
    author="Niels Lindgren",
    version=VERSION,
    packages=["eggman"],
    platforms="ANY",
    url="https://github.com/stntngo/eggman",
    install_requires=DEPENDENCIES,
    dependency_links=DEP_LINKS,
)
