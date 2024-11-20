import dspy
import os

lm = dspy.LM("openai/gpt-4o-mini", max_tokens=4000, temperature=0.0)
dspy.configure(lm=lm)


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


translator = dspy.ChainOfThought(OpenCypherTranslator)

path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)
translator.load(os.path.join(dir_path, "opencypher_translate_optimised.json"))
