from dotenv import load_dotenv
from llama_index.core import PromptTemplate
from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.response_synthesizers import BaseSynthesizer, TreeSummarize
from llama_index.llms.openai import OpenAI

# from reranker import Reranking
from src.retrieval import HybridSearch

load_dotenv()


class Generate:
    def __init__(self) -> None:
        self.search = HybridSearch()
        # self.reranker = Reranking()
        self.prompt_str = """You are an AI assistant specializing in answering user queries. Your task is to provide a clear, concise, and informative explanation based on the following context and query.

        Context:
        {context_str}

        Query: {query_str}

        Please follow these guidelines in your response:
        1. Start with a brief overview of the concept mentioned in the query.
        2. Provide at least one concrete example or use case to illustrate the concept.
        3. If there are any limitations or challenges associated with this concept, briefly mention them.
        4. Conclude with a sentence about the potential future impact or applications of this concept.

        Your explanation should be informative yet accessible, suitable for someone with a basic understanding of RAG. If the query asks for information not present in the context, please state that you don't have enough information to provide a complete answer, and only respond based on the given context.

        Response:
        """
        self.prompt_tmpl = PromptTemplate(self.prompt_str)

    def prompt_generation(self, query: str):
        results = self.search.query_hybrid_search(query)
        # reranked_documents = self.reranker.rerank_documents(query, results)

        context = "\n\n".join(results)

        prompt_templ = self.prompt_tmpl.format(context_str=context, query_str=query)

        return prompt_templ


class RagQueryEngine(CustomQueryEngine):
    llm: OpenAI
    response_synthesizer: BaseSynthesizer

    def custom_query(self, prompt: str) -> str:
        response = self.llm.complete(prompt)
        summary = self.response_synthesizer.get_response(
            query_str=str(response), text_chunks=str(prompt)
        )

        return str(summary)


def create_query_engine(prompt: str):
    llm = OpenAI(model="gpt-4o-mini")
    response_synthesizer = TreeSummarize(llm=llm)

    query_engine = RagQueryEngine(
        llm=llm,
        response_synthesizer=response_synthesizer,
    )
    response = query_engine.query(prompt)
    return response.response


if __name__ == "__main__":
    query_str = "What are the key features of Genezio as an AWS Lambda alternative?"
    prompt_gen = Generate()
    prompt = prompt_gen.prompt_generation(query=query_str)
    response = create_query_engine(prompt)
    print(response)
