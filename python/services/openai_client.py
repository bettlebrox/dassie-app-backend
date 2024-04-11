from openai import OpenAI
import logging
import json

logger = logging.getLogger()


class OpenAIClient:
    THEME_SUMMARY_PROMPT = """
        Your task is to summarise the common theme and any disagreements from the following texts seperated by three dashes.
        Output in JSON format. Including the following:
        summary, summary of common theme.
        disagreement, summary of disagreements.
        themes, list of common themes.
        disagreements, list of disagreements.

        {}
    """
    ARTICLE_SUMMARY_PROMPT = """
        Your task is to summarise the following text and pick up to three themes that appear in the text.
        Output in JSON format. Including the following:
        summary, summary of the text.
        themes, list of themes up to a maximum of three.

        {}

    """

    def __init__(self, api_key):
        self.openai_client = OpenAI(api_key=api_key)

    def get_embedding(self, article, model="text-embedding-ada-002"):
        article = article.replace("\n", " ")
        try:
            response = self.openai_client.embeddings.create(
                input=[article],
                model=model,
            )
            return response.data[0].embedding
        except Exception as error:
            logger.error(f"get_embeddings Error: {error}")
            return None

    def get_completion(self, prompt, model="gpt-3.5-turbo"):
        messages = [{"role": "user", "content": prompt}]
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,  # this is the degree of randomness of the model's output
            )
            return json.loads(response.choices[0].message.content)
        except Exception as error:
            logger.error(f"get_completion Error: {error}")
            return None

    def get_article_summarization(self, article):
        return self.get_completion(self.ARTICLE_SUMMARY_PROMPT.format(article))

    def get_theme_summarization(self, texts):
        return self.get_completion(
            self.THEME_SUMMARY_PROMPT.format("---/n".join(texts))
        )
