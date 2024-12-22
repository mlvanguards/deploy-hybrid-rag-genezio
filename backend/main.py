import os
import shutil
import tempfile
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile

from src.indexing import DocumentProcessor, QdrantIndexer
from src.schemas import ProcessingResponse, SearchResponse
from src.search import Generate, create_query_engine

app = FastAPI(
    title="Document Search API",
    description="API for processing, indexing and searching documents using hybrid search",
    version="1.0.0",
)


@app.post("/index/", response_model=ProcessingResponse)
async def index_documents(files: List[UploadFile] = File(...)):
    """
    Process and index PDF documents.
    """
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Save uploaded files to temporary directory
            for file in files:
                if not file.filename.lower().endswith(".pdf"):
                    raise HTTPException(
                        status_code=400, detail=f"File {file.filename} is not a PDF"
                    )

                file_path = os.path.join(temp_dir, file.filename)
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

            # Process documents
            processor = DocumentProcessor()
            nodes, error = processor.process_documents(temp_dir)

            if error:
                raise HTTPException(status_code=400, detail=error)

            # Initialize indexer and setup collection
            indexer = QdrantIndexer()
            indexer.setup_collection(nodes[0].text)

            # Index documents
            success = indexer.index_documents(nodes)

            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Some batches failed during indexing. Check logs for details.",
                )

            return ProcessingResponse(
                success=True,
                message="Documents processed and indexed successfully",
                document_count=len(nodes),
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/", response_model=SearchResponse)
async def search_documents(query: str):
    """
    Perform hybrid search on indexed documents.
    """
    try:
        prompt_gen = Generate()
        prompt = prompt_gen.prompt_generation(query=query)
        response = create_query_engine(prompt)

        return SearchResponse(response=response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/health/")
async def health_check():
    """
    Basic health check endpoint.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)