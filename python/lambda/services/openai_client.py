from openai import OpenAI
import logging
import json
import tiktoken
from wandb.sdk.data_types.trace_tree import Trace
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class OpenAIClient:
    MODEL = "gpt-3.5-turbo"
    CONTEXT_WINDOW_SIZE = 15000
    THEME_SUMMARY_PROMPT = """
        Your task is to summarize the common theme and any disagreements from the following texts separated by three dashes.
        Output in JSON format. Including the following:
        title, title of the theme.
        summary, summary of common theme. Do not include a preamble for example 'The common theme among the texts is'
        disagreement, summary of disagreements.
        themes, list of common themes up to a maximum of three.
        disagreements, list of disagreements up to a maximum of three.
        ---
    """
    ARTICLE_SUMMARY_PROMPT = """
        Your task is to summarize the following text and select up to three themes that appear in the text.
        Output in JSON format. Including the following:
        summary, brief summary of the text up to 100 words. Do not include a preamble for example 'The text discusses'.
        themes, list of themes up to a maximum of three.
        ---
    """

    TEMPERATURE = 0

    def __init__(self, api_key):
        self.openai_client = OpenAI(api_key=api_key)

    def get_embedding(self, article, model="text-embedding-ada-002"):
        article = article.replace("\n", " ")
        try:
            logger.info(f"get_embeddings: {article}")
            response = self.openai_client.embeddings.create(
                input=[article],
                model=model,
            )
            return response.data[0].embedding
        except Exception as error:
            logger.error(f"get_embeddings Error: {error}")
            return None

    def get_completion(self, prompt, query, model=MODEL):
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": query},
        ]
        start_time_ms = datetime.now().timestamp() * 1000
        try:
            result = True
            response = None
            try:
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=self.TEMPERATURE,
                )
                logger.info(
                    f"""get_completion response - length:{len(response.choices)}, 
                    response: {response.choices[0].message.content}"""
                )
            except Exception as error:
                logger.error(
                    f"get_completion Error: {error}: Message: {response.choices[0].message.content}",
                    exc_info=True,
                )
                result = False
                response = error
            end_time_ms = round(datetime.now().timestamp() * 1000)
            root_span = self.get_wandb_root_span(
                result, response, start_time_ms, end_time_ms, prompt, query
            )
            root_span.log(name="openai")
            return json.loads(response.choices[0].message.content)
        except Exception as error:
            logger.error(f"get_completion Error: {error}", exc_info=True)
            return None

    def get_wandb_root_span(
        self, result, response, start_time_ms, end_time_ms, prompt, query
    ):
        return Trace(
            name="get_completion",
            kind="llm",
            status_code="success" if result else "error",
            status_message=(None,) if result else str(response),
            metadata={
                "temperature": self.TEMPERATURE,
                "token_usage": response.usage.to_dict() if result else {},
                "model_name": self.MODEL,
            },
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            inputs={"prompt": prompt, "query": query},
            outputs={
                "response": (response.choices[0].message.content if result else "")
            },
        )

    def get_article_summarization(self, article):
        return self.get_completion(self.ARTICLE_SUMMARY_PROMPT, article)

    def get_theme_summarization(self, texts):
        return self.get_completion(self.THEME_SUMMARY_PROMPT, "\n---\n".join(texts))

    def count_tokens(self, text, model=MODEL):
        encoding = tiktoken.encoding_for_model(model)
        num_tokens = len(encoding.encode(text))
        return num_tokens
