# -*- coding: utf-8 -*-
import os
import boto3
import threading
from aws_requests_auth.aws_auth import AWSRequestsAuth

class AwsSessionCache(object):

    __sessionCache = dict()
    __sessionCacheLock = threading.Lock()

    def getOrCreateSession(self, region_name: str, profile_name: str):

        key = str(threading.get_ident())
        key += "|"
        if region_name:
            key += region_name
        key += "|"
        if profile_name:
            key += profile_name

        self.__sessionCacheLock.acquire()
        try:
            if key not in self.__sessionCache:
                self.__sessionCache[key] = boto3.session.Session(
                    region_name=region_name,
                    profile_name=profile_name)
            session = self.__sessionCache[key]
        finally:
            self.__sessionCacheLock.release()

        return session

awsSessionCache = AwsSessionCache()

class RefeshableAWSRequestsAuth(AWSRequestsAuth):
    """
    A class ensuring that AWS request signing uses a refreshed credential
    """

    def __init__(self,
                 refreshable_credential,
                 aws_host,
                 aws_region,
                 aws_service):
        """
        :param refreshable_credential: A credential class that refreshes STS or IAM Instance Profile credentials
        :type refreshable_credential: :class:`botocore.credentials.RefreshableCredentials`
        """
        self.refreshable_credential = refreshable_credential
        self.aws_host = aws_host
        self.aws_region = aws_region
        self.service = aws_service

    @property
    def aws_access_key(self):
        return self.refreshable_credential.access_key

    @property
    def aws_secret_access_key(self):
        return self.refreshable_credential.secret_key

    @property
    def aws_token(self):
        return self.refreshable_credential.token


class Auth(object):

    def __call__(self, host, username, password, aws_region, profile_name):
        """ Return the authorization header.

        :param host: Elasticsearch host.
        :param username: Username used for authenticating the requests to Elasticsearch.
        :param password: Password used for authenticating the requests to Elasticsearch.
        :param aws_region: AWS Region to use. Only required when signing requests.
        :param profile_name: AWS profile to use for connecting. Only required when signing requests.
        """
        if username and password:
            return username + ':' + password

        if not aws_region and not os.environ.get('AWS_DEFAULT_REGION'):
            return None

        session = awsSessionCache.getOrCreateSession(
            region_name=aws_region,
            profile_name=profile_name)

        return RefeshableAWSRequestsAuth(
            refreshable_credential=session.get_credentials(),
            aws_host=host,
            aws_region=session.region_name,
            aws_service='es')
