from datetime import datetime, timedelta
import uuid

import pytest
from models.article import Article
from lambda_init_context import LambdaInitContext
from dotenv import load_dotenv
from langfuse.decorators import observe
from langfuse.decorators import langfuse_context
from tests.integ.test_integration import GITHUB_ACTIONS


@pytest.mark.skipif(GITHUB_ACTIONS, reason="no environment yet")
@pytest.fixture
def init_context() -> LambdaInitContext:
    assert load_dotenv("tests/integ/lambda/local.env")
    init_context = LambdaInitContext()
    langfuse_context.configure(
        secret_key=init_context.lang_fuse_secret,
        public_key="pk-lf-b2888d04-2d31-4b07-8f53-d40d311d4d13",
        host="https://cloud.langfuse.com",
        release="test",
        enabled=True,
    )
    return init_context


@observe(name="test_process_theme_graph_success")
def test_process_theme_graph_success(init_context: LambdaInitContext):
    articles_service = init_context.article_service
    test_article = Article(original_title="test", url="test")
    test_article.text = 'Skip to main content\nSign Up\nLog In\n\u200b\n\u200b\nKeybind to rerun or debug last test in VSCode?\nEditors and IDEs\nJul 2023\n1 / 4\nJul 2023\nOct 2023\nhehaoqian\n1\nJul 2023\n\nHow to use keyboard only, without using mouse to rerun last Rust test,\nusing Rust analyzer in VSCode?\n\nThe VSCode System keybindings\n"Test: Debug Last Run": Ctrl + ; Ctrl + L\n"Test: Rerun Last Run": Ctrl + ; L\ndoes not work.\n\n Solved by kpreid in post #2\nYou want \u201cTasks: Rerun Last Task\u201d workbench.action.tasks.reRunTask.\n1\n1.4k\nviews\nkpreid\nJul 2023\n\nYou want \u201cTasks: Rerun Last Task\u201d workbench.action.tasks.reRunTask.\n\nSolution\nhehaoqian\nkpreid\nJul 2023\n\nThanks. It works!\n\nIn Settings->Keyboard Shortcuts, search "Tasks: Rerun Last Task" to set keybind\n\n3 months later\n\nClosed on Oct 4, 2023\n\nThis topic was automatically closed 90 days after the last reply. We invite you to open a new topic if you have further questions or comments.\n\nReply\n\n\nRelated topics\nTopic list, column headers with buttons are sortable.\nTopic\tReplies\tViews\tActivity\n\nHow to run the most recent testcase with shortcut key in vscode?\nEditors and IDEs\n\t2\t930\tDec 2023\n\nQuick and dirty fast rust test runner for VSCode\nEditors and IDEs\n\t1\t644\tMar 2023\n\nVisual Studio Code and Rust keybinding\n\t3\t503\tDec 2022\n\nChange the default \u2018Run\u2019 settings for the Rust-Analyzer plugin in VS Code\nEditors and IDEs\n\t5\t3.0k\tMay 2022\n\nVSCode: How to \u201cRun without debugging\u201d?\nEditors and IDEs\n\t3\t9.0k\tOct 2020'
    test_article._id = "test-" + str(uuid.uuid4())
    test_article._updated_at = datetime.now() - timedelta(days=2)
    try:
        graph = articles_service._process_article_graph(test_article)
    except Exception as e:
        raise e
    assert graph is not None
    try:
        init_context.neptune_client.delete_article_graph(test_article._id)
    except Exception as e:
        assert False, f"Error during cleanup: {e}"
