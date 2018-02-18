Py-SEED
=======

A python API client for the SEED Platform


Documentation
-------------
This provides two user authentication based Python clients and two OAuth2 authentication based Python clients for interacting with the SEED Platform Api::


    SEEDOAuthReadOnlyClient
    SEEDOAuthReadWriteClient
    SEEDReadOnlyClient
    SEEDReadWriteClient


(The OAuthMixin is constructed around the the JWTGrantClient found in jwt-oauth2lib. see https://github.com/GreenBuildingRegistry/jwt_oauth2)

SEED (Standard Energy Efficiency Data Platform™) is an open source "web-based application that helps organizations easily manage data on the energy performance of large groups of buildings" funded by the United States Department of Energy.

More information can be found here:
* https://energy.gov/eere/buildings/standard-energy-efficiency-data-platform
* http://seedinfo.lbl.gov/
* https://github.com/SEED-platform


Note the clients do not provide per api-call methods, but does provide the standard CRUD methods: get, list, put, post, patch, delete

The intended use of these clients is to be futher subclassed or wrapped in functions to provide the desired functionality. The CRUD methods are provided via mixins so its possible to create a client for example without the ability to delete by subclassing SEEDUserAuthBaseClient, or SEEDOAuthBaseClient, and adding only the mixins that provided the Create, Read and Update capabilities.

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


Contributing
------------

License
-------
py-SEED is released under the terms of the MIT license. Full details in LICENSE file.

Changelog
---------
py-SEED was developed for use in the greenbuildingregistry project.
For a full changelog see `CHANGELOG.rst <https://github.com/GreenBuildingRegistry/py-seed/blob/master/CHANGELOG.rst>`_.

N.B. this client is undergoing development and should be considered experimental.
