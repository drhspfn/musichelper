import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name='music-helper',
    version='2.0.4',
    description='Asynchronous library for working with streaming services. Search, download',
    author='drhspfn',
    author_email="jenya.gsta@gmail.com",
    packages=setuptools.find_packages(),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/drhspfn/music-helper",
    install_requires=[
        "aiofiles",
        "soundcloud-v2",
        "cryptography",
        "mutagen",
        "eyed3",
        "pytube",
        "ytmusicapi",
        "httpx[http2]",
        "yarl",
        "asyncio"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent"
    ],

)
