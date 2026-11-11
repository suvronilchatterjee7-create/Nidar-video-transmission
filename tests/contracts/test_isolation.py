"""CT-02: a failing item becomes error_message naming component/operation/input; the pipeline continues.
[ADIAT-inspired: StreamAnalyzeService failure isolation]"""
from __future__ import annotations

from nidar.common.contracts import run_isolated
from nidar.common.stub import stub


def test_ct02_failure_is_isolated() -> None:
    def work(i: int) -> int:
        if i == 2:
            raise ValueError("bad frame")
        if i == 3:
            raise stub("demo.component", "P1 Eq. 1")
        return i * 10

    results = [run_isolated("video.encoder", "encode", lambda i=i: work(i), gop_index=i) for i in range(5)]
    assert [r.payload for r in results] == [0, 10, None, None, 40]
    assert "video.encoder" in results[2].error_message and "gop_index=2" in results[2].error_message
    assert "ValueError" in results[2].error_message
    assert "NotYetImplemented" in results[3].error_message
    assert all(r.timings.duration_s >= 0 for r in results)
