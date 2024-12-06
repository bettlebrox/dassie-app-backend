import dspy
import os
from langfuse.decorators import observe
from langfuse.decorators import langfuse_context
from typing import Literal


class OpenCypherTranslator(dspy.Signature):
    """
    Translate RDF to OpenCypher. Assume entities may already exist in the graph. Include a SOURCE_OF relationship between the article and the entities.
    """

    question: str = dspy.InputField(
        desc="RDF turtle description of the subjects of a webpage"
    )
    article_id: str = dspy.InputField(desc="ID of the source article")
    response: str = dspy.OutputField(
        desc="OpenCypher query that creates the grounded entities and relations"
    )


class OpenCypherTranslatorClient:
    _translator: dspy.ChainOfThought

    def __init__(self):
        lm = dspy.LM("openai/gpt-4o-mini", max_tokens=4000, temperature=0.0)
        dspy.configure(lm=lm)
        self._translator = dspy.ChainOfThought(OpenCypherTranslator)
        self._translator.load(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "opencypher_translate_optimised.json",
            )
        )

    @observe(as_type=Literal["generation"])
    def translate_to_opencypher(self, entities, article_text, article_id):
        return self._translator(
            question=entities + "\n---\n" + article_text, article_id=article_id
        ).response

    @observe()
    def generate_article_graph(self, article_text, article_id, entities):
        langfuse_context.update_current_trace(
            input={"article_id": article_id},
        )
        if entities is None:
            return None
        response = self.translate_to_opencypher(entities, article_text, article_id)
        return self._get_opencypher_code_block(response)

    def _get_opencypher_code_block(self, open_cypher):
        code_block = open_cypher.strip()
        for delimiter in [
            "```opencypher",
            "```cypher",
            "```",
        ]:
            if delimiter in code_block:
                code_block = code_block.split(delimiter, 1)[-1]
                break
        return code_block.strip("`").strip()
