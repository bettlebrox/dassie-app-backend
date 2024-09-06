import json
import tiktoken
from langfuse.decorators import langfuse_context
from langfuse.decorators import observe
from langfuse.openai import OpenAI
from dassie_logger import logger


class LLMResponseException(Exception):
    """
    Represents an exception that occurs when there is an issue with the response from the OpenAI language model.
    """

    def __init__(self, message):
        self.message = message


class OpenAIClient:
    MODEL = "gpt-3.5-turbo"
    ENCODING = tiktoken.encoding_for_model(MODEL)
    CONTEXT_WINDOW_SIZE = 15000
    MIN_TEXT_LENGTH = 1000
    THEME_SUMMARY_PROMPT = """
        Your task is to summarize the common theme, that appears in at least 2 texts, and any disagreements, between at least two texts, from the following webpages texts separated by three dashes.
        Output strictly only valid JSON object. Including the following:
        title, title of the common theme.
        summary, very concise summary of common theme starting with a noun.
        disagreement, very concise summary of disagreements if any.
        themes, list of common themes up to a maximum of three.
        disagreements, list of disagreements up to a maximum of three.
        ---
    """
    ARTICLE_SUMMARY_PROMPT = """
        Your task is to summarise the following text from a webpage and select up to three themes that appear in the text.
        Output strictly only valid JSON object. Do not include any additional text or formatting. Including the following: 
        summary, a brief summary of up to 100 words starting with a verb.
        themes, list of themes up to a maximum of three.
        ---
    """

    TEMPERATURE = 0

    def __init__(self, api_key, langfuse_key):
        self.openai_client = OpenAI(api_key=api_key)
        langfuse_context.configure(
            secret_key=langfuse_key,
            public_key="pk-lf-b2888d04-2d31-4b07-8f53-d40d311d4d13",
            host="https://cloud.langfuse.com",
        )

    @observe()
    def get_embedding(self, article, model="text-embedding-ada-002"):
        article = article.replace("\n", " ")
        try:
            logger.debug("get_embedding")
            response = self.openai_client.embeddings.create(
                input=[article],
                model=model,
            )
            return response.data[0].embedding
        except Exception as error:
            logger.exception("get_embedding error")
            return None

    @observe()
    def get_completion(
        self, prompt, query, model=MODEL, min_text_length=MIN_TEXT_LENGTH
    ):
        if len(query) < min_text_length:
            logger.info("query too short")
            return None
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": query},
        ]
        try:
            response = None
            try:
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=self.TEMPERATURE,
                    response_format={"type": "json_object"},
                )
                logger.debug("get_completion response")
            except Exception as error:
                logger.exception("get_completion Error")
                response = error
            return json.loads(response.choices[0].message.content)
        except json.decoder.JSONDecodeError as error:
            logger.exception("get_completion JSON decoding Error")
            raise LLMResponseException(error)
        except Exception as error:
            logger.exception("get_completion Error")
        return None

    @observe()
    def get_article_summarization(self, article, model=MODEL):
        if len(article) < self.MIN_TEXT_LENGTH:
            logger.info("article too short")
            return None
        return self.get_completion(self.ARTICLE_SUMMARY_PROMPT, article, model=model)

    @observe()
    def get_theme_summarization(self, texts, model=MODEL):
        if not isinstance(texts, list):
            return self.get_completion(self.THEME_SUMMARY_PROMPT, texts, model=model)
        return self.get_completion(
            self.THEME_SUMMARY_PROMPT, "\n---\n".join(texts), model=model
        )

    def count_tokens(self, text, model=MODEL):
        encoding = (
            self.ENCODING if model == self.MODEL else tiktoken.encoding_for_model(model)
        )
        num_tokens = len(encoding.encode(text))
        logger.debug("count_tokens", extra={"num_tokens": num_tokens})
        return num_tokens
