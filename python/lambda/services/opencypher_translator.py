import dspy

lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)


class OpenCypherTranslator(dspy.Signature):
    """
    Translate RDF to OpenCypher. Assume entities may already exist in the graph.
    """

    question: str = dspy.InputField(
        desc="RDF turtle description of the subjects of a webpage"
    )
    response: str = dspy.OutputField(
        desc="OpenCypher query that creates the grounded entities and relations"
    )


translator = dspy.ChainOfThought(OpenCypherTranslator)
translator.load(
    "/Users/davidburke/src/dassie/dassie-app-backend/python/lambda/services/opencypher_translate_optimised.json"
)
