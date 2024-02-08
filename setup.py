import setuptools

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pgserviceparser",
    version="1.1.0",
    author="Dave Signer",
    author_email="david@opengis.ch",
    description="A package parsing the PostgreSQL connection service file.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/opengisch/pgserviceparser",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Database",
    ],
    packages=["pgserviceparser"],
    python_requires=">=3.6",
)
