import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name='musichelper',
    version='3.0.0b',
    description='Asynchronous library for working with streaming services. Search, download',
    author='drhspfn',
    author_email="jenya.gsta@gmail.com",
    packages=setuptools.find_packages(),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/drhspfn/musichelper",
    install_requires=[
        "aiofiles",
        "soundcloud-v2",
        "cryptography",
        "mutagen",
        "eyed3",
        "pytube",
        "ytmusicapi",
        "httpx[http2]",
        "yarl"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent"
    ],
)
