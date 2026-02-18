from backend.pipeline import PrivGuardPipeline

pipeline = PrivGuardPipeline()


def test_pipeline_run():
    result = pipeline.run("data/test.txt")

    assert "findings" in result
    assert "risk" in result
    assert "file" in result
