# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from urlparse import urlparse

# package shotgun_api3 until toolkit upgrades to a version that
# allows for user based logins
from .shotgun_api3 import Shotgun, MissingTwoFactorAuthenticationFault

from .login import Login
from .login import LoginError

from .login_dialog_sg import LoginDialog

from .qt_abstraction import QtCore


################################################################################
# Shotgun Login Implementation
class ShotgunLogin(Login):
    def __init__(self):
        """ Override the default constructor """
        Login.__init__(self, LoginDialog)
        self._http_proxy = None

    def set_default_login(self, login):
        """
        Set the default value for the login field in the login dialog.

        :param login: A string to set the field to
        """
        self._dialog_kwargs["default_login"] = login

    def set_default_site(self, site):
        """
        Set the default value for the site field in the login dialog.

        :param login: A string to set the field to
        """
        self._dialog_kwargs["default_site"] = site

    def set_http_proxy(self, http_proxy):
        """
        Set the proxy to use when connecting to Shotgun.

        :param http_proxy: A string which will be passed to the Shotgun constructor
            as documented here:
            https://github.com/shotgunsoftware/python-api/wiki/Reference%3A-Methods#shotgun
        """
        self._http_proxy = http_proxy

    def get_http_proxy(self):
        """
        Get the proxy to use when connecting to Shotgun.

        :returns: The proxy string.
        """
        return self._http_proxy 

    def get_login(self, site=None, dialog_message=None, force_dialog=False):
        """ Returns the HumanUser for the current login.  Acts like login otherwise. """
        results = self.login(site, dialog_message, force_dialog)
        if results:
            return results["login"]
        return None

    def get_connection(self, site=None, dialog_message=None, force_dialog=False):
        """ Returns the connection for the current login.  Acts like login otherwise. """
        results = self.login(site, dialog_message, force_dialog)
        if results:
            return results.get("connection")
        return None

    def _get_keyring_values(self, site, login):
        """
        Override the base class implementation to always use a specific keyring
        but encode the site in the login.
        """
        keyring = "com.shotgunsoftware.tk-framework-shotgunlogin"
        parse = urlparse(site)
        login = "%s@%s" % (login, parse.netloc)
        return (keyring, login)

    def _get_settings(self, group=None):
        """
        Override the base class implementation to always use a specific
        organization and application for the QSettings.
        """
        settings = QtCore.QSettings("Shotgun Software", "Shotgun Login Framework")

        if group is not None:
            settings.beginGroup(group)
        return settings

    def _site_connect(self, site, login, password, auth_token=None):
        """
        Authenticate the given values in Shotgun.

        :param site: The site to login to
        :param login: The login to use
        :param password: The password to use

        :returns: A tuple of (connection, login) if successful, where connection
            is a valid Shotgun connection to site, logged in as login, and login
            is a HumanUser dictionary of the Entity on the Shotgun site representing
            this login.

        :raises: LoginError on failure.
        """
        # try to connect to Shotgun
        try:
            # make sure that the inputs to Shotgun are encoded with a supported encoding
            if site:
                site = site.encode("utf-8")
            if login:
                login = login.encode("utf-8")
            if password:
                password = password.encode("utf-8")
            if self._http_proxy:
                http_proxy = self._http_proxy.encode("utf-8")
            else:
                http_proxy = self._http_proxy

            # connect and force an exchange so the authentication is validated
            connection = Shotgun(site, login=login, password=password, http_proxy=http_proxy, auth_token=auth_token)
            connection.find_one("HumanUser", [])
        except MissingTwoFactorAuthenticationFault:
            raise LoginError("Missing two factor authentication.")
        except Exception, e:
            raise LoginError(str(e))

        try:
            user = connection.authenticate_human_user(login, password, auth_token)
            if user is None:
                raise LoginError("login not valid.")
            return {"connection": connection, "login": user}
        except Exception, e:
            raise LoginError(str(e))
