from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from main import build_digest_items, load_config
import state

app = FastAPI(title="Paper Digest API", version="1.0")


class DigestRequest(BaseModel):
    config_path: str = "config.yaml"
    write_output: bool = False
    mark_seen: bool = False


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/digest")
def create_digest(request: DigestRequest):
    try:
        config = load_config(request.config_path)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Config file not found: {request.config_path}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    result = build_digest_items(config)
    digest_items = result["digest_items"]

    if request.mark_seen:
        seen_ids = state.load_seen_ids()
        seen_ids.update(result["all_fetched_ids"])
        state.save_seen_ids(seen_ids)

    if request.write_output and config["delivery"]["method"] == "file":
        from file_writer import write_digest

        base_dir = None
        output_path = write_digest(digest_items, config["interest_description"], config["delivery"]["file"], base_dir=base_dir)
    else:
        output_path = None

    return {
        "digest_items": digest_items,
        "metadata": {
            "total_unique_papers": result["total_unique_papers"],
            "new_papers": result["new_papers"],
            "pre_filtered_candidates": result["pre_filtered_candidates"],
            "output_path": output_path,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="127.0.0.1", port=8000, log_level="info")
