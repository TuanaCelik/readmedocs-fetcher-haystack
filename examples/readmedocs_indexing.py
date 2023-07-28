from readmedocs_fetcher_haystack.readmedocs_fetcher import ReadmeDocsFetcher
import os
from dotenv import load_dotenv
from haystack import Pipeline
from haystack.nodes import MarkdownConverter, PreProcessor
from haystack.document_stores import InMemoryDocumentStore
load_dotenv()
README_API_KEY = os.getenv('README_API_KEY')

converter = MarkdownConverter(remove_code_snippets=False)
readme_fetcher = ReadmeDocsFetcher(api_key=README_API_KEY, markdown_converter=converter)

preprocessor = PreProcessor()
doc_store = InMemoryDocumentStore()

pipe = Pipeline()
pipe.add_node(component=readme_fetcher, name="ReadmeFetcher", inputs=["File"])
pipe.add_node(component=preprocessor, name="Preprocessor", inputs=["ReadmeFetcher"])
pipe.add_node(component=doc_store, name="DocumentStore", inputs=["Preprocessor"])
pipe.run(params={"ReadmeFetcher":{"slug": "nodes_overview"}})

print(doc_store.get_document_count())