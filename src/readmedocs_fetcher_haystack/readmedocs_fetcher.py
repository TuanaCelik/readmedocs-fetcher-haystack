import os
import base64
import requests
import tempfile
from typing import List, Optional
from haystack.nodes import BaseComponent, MarkdownConverter
from haystack.schema import Document

class ReadmeDocsFetcher(BaseComponent):
    outgoing_edges = 1
    
    class ReadmeAuth(requests.auth.AuthBase):
        def __init__(self, api_key: str):
            self.api_key = api_key
        
        def __call__(self, r):
            r.headers["authorization"] = f"Basic {self.readme_token()}"
            return r
        
        def readme_token(self):
            if not self.api_key:
                raise Exception("Please provide a Readem API Key")
            api_key = f"{self.api_key}"
            return base64.b64encode(api_key.encode("utf-8")).decode("utf-8")
        
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, markdown_converter: Optional[MarkdownConverter] = None):
        self.api_key = api_key
        self.auth = self.ReadmeAuth(api_key=self.api_key)
        self.base_url = base_url
        if markdown_converter is None:
            self.markdown_converter = MarkdownConverter()
        else:
            self.markdown_converter = markdown_converter
    
    def run(self, slugs: Optional[List[str]] = None, version: Optional[str] = None):
        documents = self.fetch_docs(base_url = self.base_url, slugs=slugs, version=version)
        outputs = {"documents": documents}
        return outputs, "output_1"
    
    def fetch_docs(self, base_url: Optional[str] = None, slugs: Optional[List[str]]= None, version: Optional[str] = None) -> List[Document]:
        if version is None:
            version = self.get_stable_version()
        categories = self.get_categories_slugs(version)
        available_slugs = []
        for c in categories:
            available_slugs.extend(self.get_category_docs_slugs(c, version))
        docs = []
        if slugs != None:
            if not all(item in available_slugs for item in slugs):
                raise Exception("Please provide a document slug that exists in your readme docs")
            else:
                docs = slugs
        else:
            docs = available_slugs

        bodies = {d: self.get_doc_markdown(d, version) for d in docs}
        documents = []
        with tempfile.TemporaryDirectory() as temp_dir:
            for slug, body in bodies.items():
                temp_file_path = os.path.join(temp_dir, f"{slug}.md")
                with open(temp_file_path, 'w') as temp_file:
                    temp_file.write(body)
                meta = {"version": version, "name": slug}
                if base_url is not None:
                    meta["url"] = base_url + f"/docs/{slug}"
                documents.extend(self.markdown_converter.convert(file_path=temp_file_path, meta=meta))
        return documents
    
    def run_batch(self, query: str, version: Optional[str]):
       pass

    def get_categories_slugs(self, version: str) -> List[str]:
        """
        Get all categories slugs for a given version.
        More info:
        https://docs.readme.com/main/reference/getcategories
        """
        slugs = []
        page = 1
        payload = {"x-readme-version": version}
        while True:
            url = f"https://dash.readme.com/api/v1/categories?perPage=100&page={page}"
            res = requests.get(url, json=payload, auth=self.auth, timeout=30)
            res.raise_for_status()
            categories = res.json()
            slugs.extend([c["slug"] for c in categories])
            if len(categories) < 100:
                # We reached the last page
                break
            page += 1
        return slugs

    def get_category_docs_slugs(self, slug: str, version: str) -> List[str]:
        """
        Get all docs slugs for a given category and version.
        More info:
        https://docs.readme.com/main/reference/getcategorydocs
        """
        slugs = []
        payload = {"x-readme-version": version}
        url = f"https://dash.readme.com/api/v1/categories/{slug}/docs"
        res = requests.get(url, json=payload, auth=self.auth, timeout=30)
        docs = res.json()
        for d in docs:
            slugs.append(d["slug"])
            if d["children"]:
                slugs.extend([c["slug"] for c in d["children"]])
        return slugs

    def get_doc_markdown(self, slug: str, version: str) -> str:
        """
        Get markdown for a given doc slug and version.
        More info:
        https://docs.readme.com/main/reference/getdoc
        """
        payload = {"x-readme-version": version}
        url = f"https://dash.readme.com/api/v1/docs/{slug}"
        res = requests.get(url, json=payload, auth=self.auth, timeout=30)
        res.raise_for_status()
        return res.json()["body"]

    def get_stable_version(self) -> str:
        """
        Get the first stable version from Readme, if not found raise an exception.
        """
        url = "https://dash.readme.com/api/v1/version"
        res = requests.get(url, auth=self.auth, timeout=30)
        res.raise_for_status()
        for version in res.json():
            if version["is_stable"]:
                return version["version_clean"]
        raise Exception("Can't find stable version, specifiy it with --version")