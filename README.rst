Py-SEED
=======

.. image:: https://github.com/seed-platform/py-seed/actions/workflows/ci.yml/badge.svg?branch=develop
    :target: https://github.com/seed-platform/py-seed/actions/workflows/ci.yml/badge.svg

.. image:: https://badge.fury.io/py/py-seed.svg
    :target: https://pypi.python.org/pypi/py-seed/

A python API client for the SEED Platform. This is an updated version of the Client. It is compatible with the latest version of the SEED Platform (>2.17.4). This client still has access to the previous format of generating a lower level API client by accessing `seed_client_base.SEEDOAuthReadOnlyClient`, `seed_client_base.SEEDOAuthReadWriteClient`, `seed_client_base.SEEDReadOnlyClient`, and `seed_client_base.SEEDReadWriteClient`. This lower level API is documented below under the `Low-Level Documentation`

Stakeholders
-------------

The following list of stakeholders should be considered when making changes to this module

- 179D Tax Deduction Web Application
- Earth Advantage Green Building Registry
- User scripts for managing building data
- ECAM

Documentation
-------------
The SEED client is a read-write client. To install the client run:

.. code-block:: bash

    pip install py-seed

Within Python you can use the client like this:

.. code-block:: python

    from pathlib import Path
    from pyseed.seed_client import SeedClient

    # The seed-config.json file defines the hosting locaiton and credentials for your SEED instance.
    # If running SEED locally for testing, then you can run the following from your SEED root directory:
    #    ./manage.py create_test_user_json --username user@seed-platform.org --host http://localhost:8000 --file ./seed-config.json --pyseed

    config_file = Path('seed-config.json')
    organization_id = 1
    seed_client = SeedClient(organization_id, connection_config_filepath=config_file)

    # Get/create the new cycle and upload the data. Make sure to set the cycle ID so that the
    # data end up in the correct cycle
    cycle = seed_client.get_or_create_cycle(
        'pyseed-api-test', date(2021, 6, 1), date(2022, 6, 1), set_cycle_id=True
    )

    seed_client.upload_and_match_datafile(
        'pyseed-properties-test',
        'tests/data/test-seed-data.xlsx',
        'Single Step Column Mappings',
        'tests/data/test-seed-data-mappings.csv'
    )

    # See the projects unit tests for more examples.

Low-Level Documentation
-----------------------
This provides two user authentication based Python clients and two OAuth2 authentication based Python clients for interacting with the SEED Platform Api::


    SEEDOAuthReadOnlyClient
    SEEDOAuthReadWriteClient
    SEEDReadOnlyClient
    SEEDReadWriteClient



(The OAuthMixin is constructed around the the JWTGrantClient found in jwt-oauth2lib. see https://github.com/GreenBuildingRegistry/jwt_oauth2)

SEED (Standard Energy Efficiency Data Platform™) is an open source "web-based application that helps organizations easily manage data on the energy performance of large groups of buildings" funded by the United States Department of Energy.

More information can be found here:

* https://energy.gov/eere/buildings/standard-energy-efficiency-data-platform
* https://seed-platform.org
* https://github.com/SEED-platform
* https://buildingdata.energy.gov/#/seed


Note the clients do not provide per api-call methods, but does provide the standard CRUD methods: get, list, put, post, patch, delete

The intended use of these clients is to be further subclassed or wrapped in functions to provide the desired functionality. The CRUD methods are provided via mixins so its possible to create a client for example without the ability to delete by subclassing SEEDUserAuthBaseClient, or SEEDOAuthBaseClient, and adding only the mixins that provided the Create, Read and Update capabilities.

Basic usage for the provided clients is below.

Usage:


.. code-block:: python

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

License
-------
Full details in LICENSE file.

Changelog
---------
py-SEED was developed for use in the greenbuildingregistry project but has been extended for various uses, including Salesforce data transfer and SEED data analysis.

For a full changelog see `CHANGELOG.rst <https://github.com/seed-platform/py-seed/blob/master/CHANGELOG.rst>`_.

Releasing
---------

* Merge down to main
* Tag release on GitHub and add in the change log
* Release via command line

.. code-block:: bash

    rm -rf dist
    python setup.py sdist
    pip install twine
    twine upload dist/*
