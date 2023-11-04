import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="slobsterble-finnlidbetter",
    version="0.0.1",
    author="Finn Lidbetter",
    author_email="finnlidbetter@gmail.com",
    description="Turn-based crossword game web app.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/finnlidbetter/slobsterble/",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Unknown classifier",
    ],
    python_requires=">=3.11",
)
