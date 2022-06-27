import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pgserviceparser",
    version="1.1.0",
    author="Dave Signer",
    author_email="david@opengis.ch",
    description="A package parsing the PostgreSQL connection service file. ",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/opengisch/pgserviceparser",
    classifiers=[
        'Topic :: Database',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=['pgserviceparser'],
    python_requires=">=3.6",
)