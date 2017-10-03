# Py-SEED: ap API client for the SEED Platform

This provides two Python clients for interacting with the SEED Platform Api.
(One is read only).

SEED (Standard Energy Efficiency Data Platform™) is an open source
"web-based application that helps organizations easily manage data on the
energy performance of large groups of buildings" funded by the United States
Department of Energy.

More information can be found here:
* https://energy.gov/eere/buildings/standard-energy-efficiency-data-platform
* http://seedinfo.lbl.gov/
* https://github.com/SEED-platform


Note the clients do not provide per api-call methods, but does provide
the standard CRUD methods: get, list, put, post, patch, delete

The intended use of these clients is to be futher subclassed or wrapped in
functions to provide the desired functionality. The CRUD methods are provided
via mixins so its possible to create a client for example without the ability
to delete by subclassing SEEDBaseClient and adding only the mixins
that provided the Create, Read and Update capabilities.

Basic usage for the provided clients is below.

Usage:
```python
from pyseed import SEEDReadWriteClient

seed_client = SEEDReadWriteClient(
    your_org_id,
    username=your_username,
    password=your_password,
    base_url=url_of_your_seed_host,
    )

# list all properties
seed_client.list(endpoint='properties')

# get a single property
seed_client.get(property_pk, endpoint='properties')

N.B. this client is undergoing development and should be considered
experimental.
```
