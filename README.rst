py-SEED
===========

.. image:: https://github.com/seed-platform/py-seed/actions/workflows/ci.yml/badge.svg?branch=develop
    :target: https://github.com/seed-platform/py-seed/actions/workflows/ci.yml/badge.svg

.. image:: https://badge.fury.io/py/py-seed.svg
    :target: https://pypi.python.org/pypi/py-seed/

py-SEED serves as a Python client for the SEED Platform API. This library is purpose-built for Python applications, enabling interaction with the SEED Platform API to access property lists, create properties, establish connections, and retrieve data from ENERGY STAR(R) Portfolio Manager, BETTER, and other sources. The SEED Platform has a robust API, granting users access to every front-end feature seamlessly via the API. Currently, this library exposes the most commonly used SEED API endpoints and will undergo continuous updates tailored to the community's evolving needs. py-SEED offers two interaction levels: a high-level API providing familiar endpoints for easy connectivity to SEED's API, and a low-level API that allows read-write access to any SEED API, demanding a deeper understanding of the SEED API architecture

py-SEED is compatible with the latest version of the SEED Platform (>2.17.4) and only support SEED API Version 3.

More information can be found here:

* https://seed-platform.org
* https://energy.gov/eere/buildings/standard-energy-efficiency-data-platform
* https://github.com/SEED-platform
* https://buildingdata.energy.gov/#/seed
* https://github.com/SEED-platform/pyseed-examples


Compatibility Matrix
--------------------

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - py-SEED Version
     - SEED Version
   * - 0.5.0
     - 3.1.0
   * - 0.4.3
     - 2.21.0 - 3.0.0

Stakeholders
-------------

The following list of stakeholders should be considered when making changes to this module

* 179D Tax Deduction Web Application
* Earth Advantage Green Building Registry
* User scripts for managing building data
* ECAM

Documentation
-------------
The SEED client is a read-write client. To install the client run:

.. code-block:: bash

    pip install py-seed

Within Python you can use the client like this:

.. code-block:: python

    from pathlib import Path
    from pyseed.seed_client import SeedClient

    # The seed-config.json file defines the hosting location and credentials for your SEED instance.
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

    # See the projects unit tests for more examples. https://github.com/SEED-platform/py-seed/blob/develop/tests/test_seed_client.py
    # Or look at the py-SEED examples repository: https://github.com/SEED-platform/pyseed-examples

Low-Level Documentation
-----------------------
This client has access to the lower level API client by accessing `seed_client_base.SEEDOAuthReadOnlyClient`, `seed_client_base.SEEDOAuthReadWriteClient`, `seed_client_base.SEEDReadOnlyClient`, and `seed_client_base.SEEDReadWriteClient`. This provides two user authentication based Python clients and two authentication methods, basic and `OAuth2 <https://github.com/GreenBuildingRegistry/jwt_oauth2>`_. More information on authentication can be seen in the following py-SEED classes:

.. code-block:: bash

    SEEDOAuthReadOnlyClient
    SEEDOAuthReadWriteClient
    SEEDReadOnlyClient
    SEEDReadWriteClient

Note the clients do not provide per api-call methods, but does provide the standard CRUD methods: get, list, put, post, patch, delete. The intended use of these clients is to be further subclassed or wrapped in functions to provide the desired functionality. The CRUD methods are provided via mixins so its possible to create a client for example without the ability to delete by subclassing SEEDUserAuthBaseClient, or SEEDOAuthBaseClient, and adding only the mixins that provided the Create, Read and Update capabilities. Basic usage for the provided low-level clients is as follows:


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

Testing
-------

Tests can be run via the `pytest` command.

You will need to export environment variables for a test portfolio manager account to test integration. Environment variables should be named:

.. code-block:: bash

    SEED_PM_UN
    SEED_PM_PW


SEED Platform
-------------
SEED (Standard Energy Efficiency Data Platform™) is an open source "web-based application that helps organizations easily manage data on the energy performance of large groups of buildings" funded by the United States Department of Energy.


License
-------
Full details in LICENSE file.


Releasing
---------

This project is configured with GitHub Actions to automatically release to PyPi when a new tag is created. To release a new version:

* Create a branch with the prepared release change log
* Merge branch to develop, and open PR to main
* Once deployed to main, create a new tag in GitHub against main and copy the change log notes into the tag description
* GitHub Actions will automatically prepare the release the new version to PyPi
* Go to GitHub actions to approve the release
* After merging into main, then in the command line with the develop branch run `git merge origin main` and push the changes. This might have to be done with a person with elevated privileges to bypass the protected branch settings.

The GitHub Action required updates to the GitHub repo to only release on tags (https://github.com/SEED-platform/py-seed/settings/environments) after approval and on PyPi to add an authorized publisher (https://pypi.org/manage/project/py-SEED/settings/publishing/).
