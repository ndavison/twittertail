from app.get_twitter_values import GetTwitterValues
from app.exceptions import (
    FailedToGetTwitterValueException,
    FailedToGetTweetsException
)
import requests


class GetTweetsAPI():
    '''
    GetTweetsAPI mimmicks the process a browser uses when accessing a Twitter
    user's tweet timeline in an unauthenticated session. To do this, it:

    1. Finds the "guest token" from the Twitter markup, and uses it in the
    "x-guest-token" request header in the API call.

    2. Finds the bearer token from the Twitter main.js, and uses it in the
    "authorization" request header in the API call.

    3. Finds the user id for the supplied username from a GraphQL query.

    Arguments:
        user (str): the username of the Twitter user to query against.
    '''

    def __init__(self, user):
        self.user = user
        self.gt, self.bearer_token, self.query_id = self.__get_twitter_values()
        self.s_twitter = requests.session()
        self.headers = {
            'x-guest-token': self.gt,
            'authorization': 'Bearer %s' % (self.bearer_token),
            'content-type': 'application/json'
        }
        self.user_id = self.__get_user_id()

    def __get_twitter_values(self):
        '''
        Collect the values needed to make an unauthenticated request to the
        Twitter API for a user's timeline, using GetTwitterValues.

        Raises:
            FailedToGetTweetsException: if values could not be retrieved.

        Return:
            gt, bearer_token, query_id (tuple): the API values.
        '''

        twitter_values = GetTwitterValues()
        try:
            gt = twitter_values.get_guest_token()
            bearer_token = twitter_values.get_bearer_token()
            query_id = twitter_values.get_query_id()
        except FailedToGetTwitterValueException as e:
            raise FailedToGetTweetsException(e)
        return (gt, bearer_token, query_id)

    def __get_user_id(self):
        '''
        Gets the id of the Twitter username supplied, by querying the GraphQL
        API's "UserByScreenName" operation.

        Raises:
            FailedToGetTweetsException: if the user id could not be retrieved.

        Returns:
            user_id (str): the user id.
        '''
        user_id = None
        url = (
            'https://api.twitter.com/graphql/%s/UserByScreenName'
            % (self.query_id)
        )
        params = {
            'variables': (
                '{"screen_name":"%s","withHighlightedLabel":true}'
                % (self.user)
            )
        }
        try:
            r = self.s_twitter.get(
                url,
                params=params,
                headers=self.headers
            )
            graph_ql_json = r.json()
        except Exception as e:
            raise FailedToGetTweetsException(
                'Failed to get the user id, request excepted with: %s'
                % (str(e))
            )
        try:
            user_id = graph_ql_json['data']['user']['rest_id']
        except KeyError:
            raise FailedToGetTweetsException(
                'Failed to get the user id, could not find user rest_id in GraphQL response'
            )
        return user_id

    def get_tweets(self, count=10):
        '''
        Queries the Twitter API using a guest token and authorization bearer
        token retrived from GetTwitterValues().

        Arguments:
            count (int): the amount of tweets to get.

        Raises:
            FailedToGetTweetsException: if tweets could not be retrieved.

        Returns:
            tweets (list): a list of tweet text for the user, most recent first, limited by the 'limit' argument.
        '''

        tweets = []
        try:
            url = (
                'https://api.twitter.com/2/timeline/profile/%s.json'
                % self.user_id
            )
            # the 'count' param in this query is actually a maximum,
            # where deleted or suspended tweets are removed after the
            # count is applied, so we don't rely on this param to
            # apply the count limit we want.
            params = {
                'tweet_mode': 'extended'
            }
            r = self.s_twitter.get(url, headers=self.headers, params=params)
            timeline_json = r.json()
        except Exception as e:
            raise FailedToGetTweetsException(
                'Failed to get tweets, request excepted with: %s'
                % (str(e))
            )
        try:
            tweets_json = timeline_json['globalObjects']['tweets']
            tweet_ids = list(int(x) for x in tweets_json.keys())
            tweet_ids.sort(reverse=True)
            tweets = (
                [' '.join(tweets_json[str(x)]['full_text'].splitlines()) for x in tweet_ids[:count]]
            )
        except KeyError as e:
            raise FailedToGetTweetsException('Failed to get tweets')
        return tweets