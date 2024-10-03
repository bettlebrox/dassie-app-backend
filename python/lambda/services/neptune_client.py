import boto3
import re


from dassie_logger import logger


class NeptuneClient:
    _endpoint = "https://127.0.0.1:8182"

    def __init__(self, endpoint):
        self._endpoint = endpoint
        session = boto3.Session()
        self.client = session.client("neptunedata", endpoint_url=endpoint, verify=False)

    def query(
        self,
        query,
    ):
        try:
            query = self._remove_unsupported_from_query(query)
            logger.info(f"Neptune query: {query}")
            response = self.client.execute_open_cypher_query(openCypherQuery=query)
            logger.info(f"Neptune query response: {response}")
            if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
                raise Exception(
                    f"Neptune query failed with status code: {response['ResponseMetadata']['HTTPStatusCode']}"
                )
            return response["results"]
        except Exception as e:
            logger.error(f"Error querying Neptune: {e}")
            raise e

    def _remove_unsupported_from_query(self, query):
        query = re.sub(r"(date|datetime|duration)\((('|\").*?('|\"))\)", r"\2", query)
        return query
