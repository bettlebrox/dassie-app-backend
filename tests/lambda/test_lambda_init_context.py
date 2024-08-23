import unittest
from lambda_init_context import LambdaInitContext


class TestLambdaInitContext(unittest.TestCase):

    def test_lambda_init_context_instantiation(self):
        context = LambdaInitContext()
        self.assertIsInstance(context, LambdaInitContext)

    def test_lambda_init_context_attributes(self):
        context = LambdaInitContext()
        self.assertTrue(hasattr(context, "__dict__"))

    def test_lambda_init_context_empty(self):
        context = LambdaInitContext()
        self.assertEqual(len(context.__dict__), 0)

    def test_lambda_init_context_add_attribute(self):
        context = LambdaInitContext()
        context.test_attr = "test_value"
        self.assertEqual(context.test_attr, "test_value")

    def test_lambda_init_context_multiple_attributes(self):
        context = LambdaInitContext()
        context.attr1 = 1
        context.attr2 = "two"
        context.attr3 = [3]
        self.assertEqual(context.attr1, 1)
        self.assertEqual(context.attr2, "two")
        self.assertEqual(context.attr3, [3])

    def test_lambda_init_context_attribute_modification(self):
        context = LambdaInitContext()
        context.mutable_attr = [1, 2, 3]
        context.mutable_attr.append(4)
        self.assertEqual(context.mutable_attr, [1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
